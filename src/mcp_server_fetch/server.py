from typing import Annotated, Tuple
from urllib.parse import urlparse, urlunparse
import logging
import sys
import time

import markdownify
import readabilipy.simple_json
from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from protego import Protego
from pydantic import BaseModel, Field, AnyUrl

# Set up logger
logger = logging.getLogger("mcp-fetch")

DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    logger.debug("Converting HTML content to Markdown (content length: %d bytes)", len(html))
    start_time = time.time()
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html, use_readability=True
    )
    if not ret["content"]:
        logger.warning("HTML simplification failed - no content extracted")
        return "<error>Page failed to be simplified from HTML</error>"
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )
    logger.debug(
        "HTML conversion completed in %.2f seconds (output length: %d bytes)",
        time.time() - start_time, 
        len(content)
    )
    return content


def get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL.

    Args:
        url: Website URL to get robots.txt for

    Returns:
        URL of the robots.txt file
    """
    # Parse the URL into components
    parsed = urlparse(url)

    # Reconstruct the base URL with just scheme, netloc, and /robots.txt path
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    
    logger.debug("Generated robots.txt URL: %s from base URL: %s", robots_url, url)
    return robots_url


async def check_may_autonomously_fetch_url(url: str, user_agent: str) -> None:
    """
    Check if the URL can be fetched by the user agent according to the robots.txt file.
    Raises a McpError if not.
    """
    from httpx import AsyncClient, HTTPError

    logger.info("Checking if URL can be autonomously fetched: %s", url)
    robot_txt_url = get_robots_txt_url(url)

    async with AsyncClient() as client:
        try:
            logger.debug("Fetching robots.txt from %s with User-Agent: %s", robot_txt_url, user_agent)
            response = await client.get(
                robot_txt_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )
            logger.debug("Robots.txt fetch status: %d", response.status_code)
        except HTTPError as e:
            logger.error("Failed to fetch robots.txt: %s", str(e))
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to fetch robots.txt {robot_txt_url} due to a connection issue",
            ))
        if response.status_code in (401, 403):
            logger.warning("Access to robots.txt denied with status code: %d", response.status_code)
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"When fetching robots.txt ({robot_txt_url}), received status {response.status_code} so assuming that autonomous fetching is not allowed, the user can try manually fetching by using the fetch prompt",
            ))
        elif 400 <= response.status_code < 500:
            logger.info("robots.txt not found (status %d) - proceeding with fetch", response.status_code)
            return
        robot_txt = response.text
    
    logger.debug("Retrieved robots.txt content (length: %d bytes)", len(robot_txt))
    processed_robot_txt = "\n".join(
        line for line in robot_txt.splitlines() if not line.strip().startswith("#")
    )
    robot_parser = Protego.parse(processed_robot_txt)
    
    can_fetch = robot_parser.can_fetch(str(url), user_agent)
    logger.info("Robots.txt check result: can_fetch=%s for URL=%s with User-Agent=%s", 
                can_fetch, url, user_agent)
    
    if not can_fetch:
        logger.warning("URL fetch blocked by robots.txt: %s", url)
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"The sites robots.txt ({robot_txt_url}), specifies that autonomous fetching of this page is not allowed, "
            f"<useragent>{user_agent}</useragent>\n"
            f"<url>{url}</url>"
            f"<robots>\n{robot_txt}\n</robots>\n"
            f"The assistant must let the user know that it failed to view the page. The assistant may provide further guidance based on the above information.\n"
            f"The assistant can tell the user that they can try manually fetching the page by using the fetch prompt within their UI.",
        ))


async def fetch_url(
    url: str, user_agent: str, force_raw: bool = False
) -> Tuple[str, str]:
    """
    Fetch the URL and return the content in a form ready for the LLM, as well as a prefix string with status information.
    """
    from httpx import AsyncClient, HTTPError
    
    logger.info("Fetching URL: %s (force_raw=%s)", url, force_raw)
    start_time = time.time()
    
    async with AsyncClient() as client:
        try:
            logger.debug("Making HTTP request to %s with User-Agent: %s", url, user_agent)
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
            logger.debug("URL fetch completed with status: %d in %.2f seconds", 
                       response.status_code, time.time() - start_time)
        except HTTPError as e:
            logger.error("Failed to fetch URL %s: %s", url, str(e))
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))
        if response.status_code >= 400:
            logger.error("URL fetch failed with status code: %d", response.status_code)
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to fetch {url} - status code {response.status_code}",
            ))

        page_raw = response.text
        logger.debug("Retrieved raw content (length: %d bytes)", len(page_raw))

    content_type = response.headers.get("content-type", "")
    is_page_html = (
        "<html" in page_raw[:100] or "text/html" in content_type or not content_type
    )
    logger.debug("Content type: %s, is_html: %s", content_type, is_page_html)

    if is_page_html and not force_raw:
        logger.info("Converting HTML to Markdown for URL: %s", url)
        content, prefix = extract_content_from_html(page_raw), ""
    else:
        logger.info("Returning raw content for URL: %s", url)
        content, prefix = (
            page_raw,
            f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
        )
    
    logger.debug("Fetch completed for %s in %.2f seconds (result length: %d bytes)", 
                url, time.time() - start_time, len(content))
    return content, prefix


class Fetch(BaseModel):
    """Parameters for fetching a URL."""

    url: Annotated[AnyUrl, Field(description="URL to fetch")]
    max_length: Annotated[
        int,
        Field(
            default=5000,
            description="Maximum number of characters to return.",
            gt=0,
            lt=1000000,
        ),
    ]
    start_index: Annotated[
        int,
        Field(
            default=0,
            description="On return output starting at this character index, useful if a previous fetch was truncated and more context is required.",
            ge=0,
        ),
    ]
    raw: Annotated[
        bool,
        Field(
            default=False,
            description="Get the actual HTML content if the requested page, without simplification.",
        ),
    ]


async def serve(
    custom_user_agent: str | None = None, ignore_robots_txt: bool = False, log_level: str = "INFO"
) -> None:
    """Run the fetch MCP server.

    Args:
        custom_user_agent: Optional custom User-Agent string to use for requests
        ignore_robots_txt: Whether to ignore robots.txt restrictions
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    logger.info("Starting MCP Fetch server (ignore_robots_txt=%s, log_level=%s)", 
               ignore_robots_txt, log_level)
    
    if custom_user_agent:
        logger.info("Using custom User-Agent: %s", custom_user_agent)
    
    server = Server("mcp-fetch")
    user_agent_autonomous = custom_user_agent or DEFAULT_USER_AGENT_AUTONOMOUS
    user_agent_manual = custom_user_agent or DEFAULT_USER_AGENT_MANUAL
    
    logger.debug("Autonomous User-Agent: %s", user_agent_autonomous)
    logger.debug("Manual User-Agent: %s", user_agent_manual)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        logger.debug("list_tools() called")
        return [
            Tool(
                name="fetch",
                description="""Fetches a URL from the internet and optionally extracts its contents as markdown.

Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.""",
                inputSchema=Fetch.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        logger.debug("list_prompts() called")
        return [
            Prompt(
                name="fetch",
                description="Fetch a URL and extract its contents as markdown",
                arguments=[
                    PromptArgument(
                        name="url", description="URL to fetch", required=True
                    )
                ],
            )
        ]

    @server.call_tool()
    async def call_tool(name, arguments: dict) -> list[TextContent]:
        logger.info("Tool called: %s with arguments: %s", name, arguments)
        try:
            args = Fetch(**arguments)
            logger.debug("Parsed arguments: url=%s, max_length=%d, start_index=%d, raw=%s", 
                        args.url, args.max_length, args.start_index, args.raw)
        except ValueError as e:
            logger.error("Invalid arguments: %s", str(e))
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        url = str(args.url)
        if not url:
            logger.error("URL is required but not provided")
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

        if not ignore_robots_txt:
            await check_may_autonomously_fetch_url(url, user_agent_autonomous)

        content, prefix = await fetch_url(
            url, user_agent_autonomous, force_raw=args.raw
        )
        original_length = len(content)
        logger.debug("Original content length: %d bytes", original_length)
        
        if args.start_index >= original_length:
            logger.warning("Invalid start_index: %d exceeds content length: %d", 
                         args.start_index, original_length)
            content = "<error>No more content available.</error>"
        else:
            truncated_content = content[args.start_index : args.start_index + args.max_length]
            if not truncated_content:
                logger.warning("No content available after applying start_index and max_length")
                content = "<error>No more content available.</error>"
            else:
                content = truncated_content
                actual_content_length = len(truncated_content)
                remaining_content = original_length - (args.start_index + actual_content_length)
                logger.debug("Truncated content length: %d bytes, remaining: %d bytes", 
                           actual_content_length, remaining_content)
                
                # Only add the prompt to continue fetching if there is still remaining content
                if actual_content_length == args.max_length and remaining_content > 0:
                    next_start = args.start_index + actual_content_length
                    logger.info("Content truncated - suggesting next start_index: %d", next_start)
                    content += f"\n\n<error>Content truncated. Call the fetch tool with a start_index of {next_start} to get more content.</error>"
        
        logger.info("Returning fetched content for URL: %s (length: %d bytes)", url, len(content))
        return [TextContent(type="text", text=f"{prefix}Contents of {url}:\n{content}")]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        logger.info("Prompt requested: %s with arguments: %s", name, arguments)
        if not arguments or "url" not in arguments:
            logger.error("URL is required but not provided in prompt arguments")
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

        url = arguments["url"]
        logger.debug("Prompt URL: %s", url)

        try:
            content, prefix = await fetch_url(url, user_agent_manual)
            logger.info("Successfully fetched content for prompt URL: %s (length: %d bytes)", 
                      url, len(content))
        except McpError as e:
            logger.error("Failed to fetch URL for prompt: %s - %s", url, str(e))
            return GetPromptResult(
                description=f"Failed to fetch {url}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=str(e)),
                    )
                ],
            )
        return GetPromptResult(
            description=f"Contents of {url}",
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=prefix + content)
                )
            ],
        )

    options = server.create_initialization_options()
    logger.info("Server initialized with options: %s", options)
    
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Starting stdio server")
        try:
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
        except Exception as e:
            logger.critical("Server crashed with exception: %s", str(e), exc_info=True)
            raise
        finally:
            logger.info("Server shutting down")