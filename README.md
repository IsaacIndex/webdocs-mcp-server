# Web Scraper MCP Server

A web scraping server that implements the Minecraft Control Protocol (MCP) using FastAPI. This server provides tools for extracting content and links from web pages in a structured way.

## Features

- Web content extraction with intelligent content cleaning
- Link extraction with full URL resolution
- Language detection
- Headless Chrome browser automation
- FastAPI-based REST API
- MCP protocol implementation

## Prerequisites

- Python 3.8+
- Chrome browser installed
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

## Running the Server

Start the server:
```bash
python main.py
```

The server will start on `http://localhost:8000` by default.

## API Endpoints

### MCP Endpoints

#### Scrape Website
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `scrape_website`
- **Parameters**:
  ```json
  {
    "url": "https://example.com"
  }
  ```
- **Response**: Extracted and cleaned content from the webpage

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
- **Response**: List of all links found on the webpage

#### Ping
- **URL**: `/mcp`
- **Method**: POST
- **Command**: `ping`
- **Response**: Server status and version information

### Health Check
- **URL**: `/health`
- **Method**: GET

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Logging

Logs are written to `~/Downloads/mcp.log` and include:
- Server startup/shutdown events
- Web scraping operations
- Error messages and exceptions

## Project Structure

- `main.py`: Core server implementation and MCP endpoints
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


