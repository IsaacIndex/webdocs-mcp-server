# Web Scraper MCP Server - Agent Guide

This guide is designed to help AI agents navigate and understand the Web Scraper MCP Server codebase.

## Project Overview

This is a FastAPI-based web scraping server that implements the Minecraft Control Protocol (MCP). The server provides structured tools for web content extraction and link parsing.

## Key Technologies

- FastAPI for the web server
- Headless Chrome for browser automation
- uv for Python package management
- Python 3.8+ as the base runtime

## Package Management with uv

This project uses `uv` as its package manager, which is a modern, fast Python package installer and resolver. Here are the key commands:

```bash
# Install dependencies
uv venv
uv pip install -r requirements.txt

# Add a new package
uv pip install package_name
```

## Project Structure

```
.
├── main.py           # Core server implementation and MCP endpoints
├── mcp.json         # MCP configuration
├── requirements.txt  # Python dependencies
├── pyproject.toml   # Project metadata
└── README.md        # Project documentation
```

## Key Components

### 1. MCP Endpoints (`main.py`)
- `/mcp` endpoint handling:
  - `scrape_website`: Extracts and cleans web content
  - `extract_links`: Retrieves all links from a webpage
  - `ping`: Server status check

### 2. Configuration
- Environment variables in `.env`:
  - `PORT`: Server port (default: 8000)
- Logging configuration:
  - Logs are written to `~/Downloads/mcp.log`

## Common Tasks

### Adding New Dependencies
1. Install using uv:
   ```bash
   uv pip install new_package
   ```
2. Update requirements.txt:
   ```bash
   uv pip freeze > requirements.txt
   ```

### Running the Server
```bash
python main.py
```
Server starts at `http://localhost:8000`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

The codebase implements comprehensive error handling for:
- Invalid URLs
- Network issues
- WebDriver failures
- Content extraction errors

## Best Practices

1. Always use uv for package management
2. Keep requirements.txt updated after adding new packages
3. Follow the existing error handling patterns
4. Maintain logging consistency
5. Document new endpoints in the README.md
6. After making changes, check if `mcp.json` or `README.md` need updates. Update `mcp.json` when endpoints or trigger words change and keep the README in sync.

## Testing

The server includes health check endpoint at `/health` for basic monitoring.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Update documentation
5. Submit a pull request 
