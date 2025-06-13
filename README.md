# MCP Server Template

A template for implementing a Minecraft Control Protocol (MCP) server using FastAPI.

## Setup

1. Install dependencies using uv:
```bash
uv pip install -r requirements.txt
```

2. Create a `.env` file (optional):
```bash
PORT=8000
```

## Running the Server

Start the server:
```bash
python server.py
```

The server will start on `http://localhost:8000` by default.

## API Endpoints

### MCP Endpoint
- **URL**: `/mcp`
- **Method**: POST
- **Request Body**:
```json
{
    "command": "string",
    "parameters": {
        "key": "value"
    }
}
```

### Health Check
- **URL**: `/health`
- **Method**: GET

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 