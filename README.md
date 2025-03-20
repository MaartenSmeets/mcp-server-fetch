![Fetch MCP Logo](https://raw.githubusercontent.com/MaartenSmeets/mcp-server-fetch/main/logo.png)
# Fetch MCP Server

A Model Context Protocol server that provides web content fetching capabilities using browser automation, OCR, and multiple extraction methods. This server enables LLMs to retrieve and process content from web pages, even those that require JavaScript rendering or use techniques that prevent simple scraping.

### Available Tools

- `fetch` - Fetches a URL from the internet using browser automation and multi-method extraction (including OCR).
    - `url` (string, required): URL to fetch
    - `raw` (boolean, optional): Get the actual HTML content if the requested page, without simplification (default: false)

The server uses multiple methods to extract content:
1. Browser automation with undetected-chromedriver
2. OCR using pytesseract with layout detection
3. HTML extraction using requests/BeautifulSoup
4. Original markdown conversion method

The server automatically selects the best result based on content quality and length.

### Prompts

- **fetch**
  - Fetch a URL and extract its contents as markdown using browser automation
  - Arguments:
    - `url` (string, required): URL to fetch

## Installation

### Using Docker

To install and run `mcp-server-fetch` using Docker, follow these steps:

1. **Build the Docker image:**
   ```bash
   docker build -t mcp-server-fetch .
   ```

2. **Run the Docker container:**
   ```bash
   docker run --rm -i mcp-server-fetch
   ```

## Configuration

### Configure Roo Code or Claude App

Add to your Claude settings:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "mcp-server-fetch"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

### Customization - User-agent

By default, depending on if the request came from the model (via a tool), or was user initiated (via a prompt), the
server will use either the user-agent
```
ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)
```
or
```
ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)
```

This can be customized by adding the argument `--user-agent=YourUserAgent` to the `args` list in the configuration.

### Browser Automation and OCR

The server now includes advanced content extraction capabilities:

- Automated handling of cookie consent banners
- Full-page screenshot capture
- OCR with layout detection using pytesseract
- Multiple extraction methods with automatic selection of best results

## Contributing

We encourage contributions to help expand and improve mcp-server-fetch. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-fetch even more powerful and useful.

## License

mcp-server-fetch is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
