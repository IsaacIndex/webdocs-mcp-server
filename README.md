# Web Scraper MCP Server

A web scraping server that implements the Minecraft Control Protocol (MCP) using FastAPI. This server provides tools for extracting content and links from web pages in a structured way.

## Features

- Web content extraction with intelligent content cleaning
- Link extraction with full URL resolution
- Language detection
- Headless browser automation with Playwright by default or Selenium when cookies are required
- Open URLs in your existing browser session
- Multi-step website actions with Playwright
- FastAPI-based REST API
- MCP protocol implementation
- Streaming agent uses a planner, a per-step executor agent, and a summarizer
  - Planner outputs `<plan>` with a list of tool names outside of `<think>`

## Prerequisites

- Python 3.11+
- Chrome browser installed
- If Chrome is not in your PATH, set the `CHROME_BINARY` environment variable to the full path of the Chrome executable
- The WebScraper can run in Playwright or Selenium mode. Playwright is the default unless cookie-based sessions are needed.
- uv package manager

## Setup

1. Create a virtual environment and install dependencies using uv:
```bash
uv venv
uv pip install -r requirements.txt
```

2. Create a `.env` file (optional):
```bash
PORT=8000
```

## Usage modes

### MCP mode

Start the server:
```bash
python mcp_server.py [--log-level info|debug|warning|error|critical]
```

The server will start on `http://localhost:8000` by default.

### Agent mode

Legacy code is kept in `agents_legacy.py` for reference.
The old `agents.py` script is deprecated. Use `agents_stream_tools.py` for models that support the tools API. For other models, run `agents_stream_prompt.py`.
Run the interactive agent with tool support:
```bash
python agents_stream_tools.py [--debug] "your question here"
```
Use the `--debug` flag to print tool calls and intermediate messages.
For models without tool support:
```bash
python agents_stream_prompt.py "your question here"
```

Both agents follow a three-part workflow:
1. **Planner** decides which tools to call and returns `<plan>` containing only tool names outside of `<think>`.
2. **Executor** runs each step using the previous tool output as context.
3. **Summarizer** uses the final tool output to answer the query.

## API Endpoints

### MCP Endpoints

#### Scrape Website
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `scrape_website`
- **Parameters**:
  ```json
  {
    "url": "https://example.com",
    "query": "specific topic"
  }
  ```
- **Response**: Filtered content relevant to the query

#### Extract Links
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `extract_links`
- **Parameters**:
```json
{
  "url": "https://example.com"
}
```
The server fetches the URL and returns all links found on the page.
- Relative paths are converted to absolute URLs based on the provided page.
- **Response**: List of all links found on the page

#### Download PDFs
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `download_pdfs`
- **Parameters**:
  ```json
  {
    "links": ["https://example.com/sample.pdf"]
  }
  ```
- **Response**: Paths to the downloaded PDF files

#### Open Browser
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `open_browser`
- **Parameters**:
  ```json
  {
    "url": "https://example.com"
  }
  ```
- **Response**: Confirmation that the URL was opened using your browser session

#### React Browser Task
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `react_browser_task`
- **Parameters**:
  ```json
  {
    "url": "https://example.com",
    "goal": "Click the next button and return the page text"
  }
  ```
- **Response**: Final page content after completing the goal

### Health Check
- **URL**: `/health`
- **Method**: GET

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Logging

Server logs are written to `project_folder/logs/mcp.log` and include:
 - Server startup/shutdown events
 - Web scraping operations
 - Error messages and exceptions
The `agents_stream_tools.py` and `agents_stream_prompt.py` script logs to `project_folder/logs/agent.log`.
Both sets of logs are stored in the same directory and the agent output captures tool calls and the `<think>` sections for full traceability.
You can adjust server verbosity with the `--log-level` flag when starting the server.
By default, server logs use the `warning` level.

## Project Structure

- `mcp_server.py`: Core server implementation and MCP endpoints
- `agents_stream_tools.py`: Interactive agent for direct tool use
- `agents_stream_prompt.py`: Agent for models without Ollama tools support
- `mcp.json`: MCP configuration file
- `requirements.txt`: Python dependencies
- `pyproject.toml`: Project metadata and build configuration

## Error Handling

The server includes comprehensive error handling for:
- Invalid URLs
- Network connectivity issues
- WebDriver initialization failures
- Content extraction errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Updating `mcp.json` Path

If you move the project directory, run the helper script to update the
`mcp.json` configuration:

```bash
python update_mcp_path.py
```

The updated JSON is copied to your clipboard so you can replace the content of
`mcp.json` easily.


