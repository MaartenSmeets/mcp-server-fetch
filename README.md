# Fetch MCP Server

A Model Context Protocol server that provides web content fetching capabilities. This server enables LLMs to retrieve and process content from web pages, converting HTML to markdown for easier consumption.

The fetch tool will truncate the response, but by using the `start_index` argument, you can specify where to start the content extraction. This lets models read a webpage in chunks, until they find the information they need.

### Available Tools

- `fetch` - Fetches a URL from the internet and extracts its contents as markdown.
    - `url` (string, required): URL to fetch
    - `max_length` (integer, optional): Maximum number of characters to return (default: 5000)
    - `start_index` (integer, optional): Start content from this character index (default: 0)
    - `raw` (boolean, optional): Get raw content without markdown conversion (default: false)

### Prompts

- **fetch**
  - Fetch a URL and extract its contents as markdown
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

## Contributing

We encourage contributions to help expand and improve mcp-server-fetch. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-fetch even more powerful and useful.

## License

mcp-server-fetch is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.