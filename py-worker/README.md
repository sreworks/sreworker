# py-worker - Python Implementation

Python implementation of the AI Code Worker Manager using FastAPI.

## Features

- ✅ Multi AI CLI support (Claude Code, OpenCode)
- ✅ Adapter pattern for easy extensibility
- ✅ File watching and stdout reading modes
- ✅ Real-time WebSocket communication
- ✅ RESTful API
- ✅ Web-based UI
- ✅ Async I/O for high performance

## Requirements

- Python 3.9+
- pip

## Quick Start

### 1. Install Dependencies

```bash
cd py-worker
pip install -r requirements.txt
```

### 2. Configure Environment

**⚠️ Important: .env File Location**

The `.env` file must be placed in the `py-worker/` directory (project root), not in subdirectories.

```bash
# Correct location
/home/twwyzh/sreworker/py-worker/.env  ✅

# Wrong locations
/home/twwyzh/sreworker/py-worker/app/.env  ❌
/home/twwyzh/sreworker/.env  ❌
```

**Setup:**

```bash
cd /home/twwyzh/sreworker/py-worker  # Make sure you're in the right directory
cp .env.example .env
# Edit .env file with your configuration
```

**Option 1: Using .env file**

Set API keys in the `.env` file:
- `CLAUDE_API_KEY` if using Claude Code
- `OPENCODE_API_KEY` if using OpenCode

**Option 2: Using system environment variables (Recommended)**

Alternatively, you can set environment variables directly:
- `ANTHROPIC_API_KEY` for Claude Code
- `OPENCODE_API_KEY` for OpenCode

The system will automatically detect and use environment variables if they're not specified in the .env file.

> 📚 For detailed information about .env file path and loading mechanism, see [ENV_PATH_GUIDE.md](./ENV_PATH_GUIDE.md)

### 3. Start the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

Or simply:

```bash
python -m app.main
```

**Startup Output**: The server will display all configuration details on startup, including:
- Server settings (host, port, debug mode)
- Worker configuration (max workers, timeout)
- AI CLI configuration (enabled CLIs, models)
- API key status (from .env or environment variables)

Example output:
```
======================================================================
Starting AI Code Worker Manager...
======================================================================

📡 Server Configuration:
  Host: 0.0.0.0
  Port: 7788
  Debug: False

⚙️  Worker Configuration:
  Max Workers: 10
  Worker Timeout: 300s

🤖 AI CLI Configuration:
  Default AI CLI: claude
  Enabled AI CLIs: claude, opencode

  🔵 Claude Code:
    Binary: claude
    Model: claude-3-5-sonnet-20241022
    API Key (from .env): Not set
    API Key (from env): sk-ant-a...xyz9 ✅

🔌 Registering Adapters...
  Registered: claude, opencode

🚀 Initializing Worker Manager...

======================================================================
✅ AI Code Worker Manager started successfully!
📍 Access at: http://0.0.0.0:7788
📚 API Docs: http://0.0.0.0:7788/docs
======================================================================
```

This helps you verify your configuration is correct before using the system.

### 4. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:7788
```

## Configuration

You can configure the application in two ways:

1. **Using .env file**: Edit the `.env` file to set configuration values
2. **Using system environment variables**: Set environment variables directly in your system

The application will first check the `.env` file, then fall back to system environment variables.

### Server Configuration
```env
HOST=0.0.0.0
PORT=7788
DEBUG=true
```

### AI CLI Configuration
```env
DEFAULT_AI_CLI=claude
ENABLED_AI_CLIS=claude,opencode

# Claude Code
CLAUDE_BINARY=claude
CLAUDE_API_KEY=your-anthropic-api-key
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# OpenCode
OPENCODE_BINARY=opencode
OPENCODE_API_KEY=your-opencode-api-key
OPENCODE_API_BASE=https://api.opencode.com
OPENCODE_MODEL=gpt-4
```

### Worker Configuration
```env
WORKERS_BASE_DIR=./data/workers
MAX_WORKERS=10
WORKER_TIMEOUT=300
```

## Project Structure

```
py-worker/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── adapters/               # AI CLI adapters
│   │   ├── base.py            # Base adapter class
│   │   ├── claude.py          # Claude Code adapter
│   │   ├── opencode.py        # OpenCode adapter
│   │   └── registry.py        # Adapter registry
│   ├── models/                 # Data models
│   │   ├── worker.py
│   │   ├── message.py
│   │   └── ai_cli.py
│   ├── services/               # Business logic
│   │   ├── worker_manager.py
│   │   ├── process_handler.py
│   │   └── file_watcher.py
│   ├── api/                    # API routes
│   │   ├── workers.py
│   │   └── websocket.py
│   └── utils/                  # Utilities
│       ├── jsonl_parser.py
│       └── logger.py
├── static/                     # Web interface
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── data/                       # Worker data
├── logs/                       # Application logs
├── requirements.txt            # Python dependencies
└── .env.example               # Environment template
```

## API Documentation

### REST API

Once the server is running, visit:
- Swagger UI: http://localhost:7788/docs
- ReDoc: http://localhost:7788/redoc

#### Key Endpoints

**List Workers**
```http
GET /api/workers
```

**Create Worker**
```http
POST /api/workers
Content-Type: application/json

{
  "name": "my-worker",
  "project_path": "/path/to/project",
  "ai_cli_type": "claude"
}
```

**Get Worker Details**
```http
GET /api/workers/{worker_id}
```

**Delete Worker**
```http
DELETE /api/workers/{worker_id}
```

**List Available AI CLIs**
```http
GET /api/ai-clis
```

### WebSocket API

**Connect to Worker**
```
ws://localhost:7788/ws/{worker_id}
```

**Send Message**
```json
{
  "type": "message",
  "content": "Your message here"
}
```

**Receive Output**
```json
{
  "type": "output",
  "timestamp": "2024-01-01T00:00:00Z",
  "content": { ... }
}
```

## Usage Examples

### Using the Web Interface

1. **Create a Worker**
   - Click "New Worker" button
   - Fill in worker name and project path
   - Select AI CLI type (Claude or OpenCode)
   - Click "Create Worker"

2. **Send Messages**
   - Select a worker from the list
   - Type your message in the input box
   - Press Enter or click "Send"

3. **View Output**
   - Worker responses appear in real-time
   - Message history is preserved

4. **Delete a Worker**
   - Select a worker
   - Click "Delete Worker" button
   - Confirm deletion

### Using the API

```python
import requests
import websocket
import json

# Create a worker
response = requests.post('http://localhost:7788/api/workers', json={
    'name': 'test-worker',
    'project_path': '/path/to/project',
    'ai_cli_type': 'claude'
})
worker = response.json()
worker_id = worker['id']

# Connect via WebSocket
ws = websocket.create_connection(f'ws://localhost:7788/ws/{worker_id}')

# Send a message
ws.send(json.dumps({
    'type': 'message',
    'content': 'Hello, AI!'
}))

# Receive responses
while True:
    message = json.loads(ws.recv())
    print(message)
```

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --reload --log-level debug
```

### Code Formatting

```bash
black app/
isort app/
```

### Type Checking

```bash
mypy app/
```

### Running Tests

```bash
pytest tests/ -v
```

## Adapter Development

To add support for a new AI CLI:

1. Create a new adapter class in `app/adapters/`
2. Inherit from `BaseWorkerAdapter`
3. Implement all required methods
4. Register the adapter in `app/adapters/registry.py`

Example:

```python
from .base import BaseWorkerAdapter

class MyCustomAdapter(BaseWorkerAdapter):
    def get_command(self, project_path: str, **kwargs) -> List[str]:
        return ["my-ai-cli", "--project", project_path]

    def needs_file_watcher(self) -> bool:
        return False  # or True if file watching is needed

    def get_log_file_path(self, project_path: str) -> Optional[str]:
        return None  # or path to log file

    def parse_output(self, line: str) -> Optional[Dict[str, Any]]:
        # Parse output format
        return json.loads(line)

    def format_input(self, message: str) -> str:
        return message + "\n"

    async def get_output_stream(self, process) -> AsyncIterator[str]:
        # Yield output lines
        async for line in process.stdout:
            yield line.decode('utf-8')
```

Then register it:

```python
from .my_custom import MyCustomAdapter

adapter_registry.register_adapter("my-custom", MyCustomAdapter, config)
```

## Troubleshooting

### Worker Creation Fails

- Check that the AI CLI binary is in PATH
- Verify API keys are correctly set in .env
- Check logs in `./logs/app.log`

### WebSocket Connection Issues

- Ensure the server is running
- Check firewall settings
- Verify the worker exists

### No Output from Worker

- For Claude Code: Check that project.jsonl file is being created
- For OpenCode: Check that the process is outputting to stdout
- Check adapter configuration

## Performance Tips

- Limit the number of concurrent workers
- Use appropriate timeout values
- Monitor system resources
- Consider using a process manager (systemd, supervisor)

## Production Deployment

### Using Gunicorn

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:7788
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7788"]
```

### Using Systemd

Create `/etc/systemd/system/py-worker.service`:

```ini
[Unit]
Description=AI Code Worker Manager
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/py-worker
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 7788
Restart=always

[Install]
WantedBy=multi-user.target
```

## License

Apache License 2.0 - See LICENSE file for details

## Contributing

Contributions are welcome! Please see the main project README for guidelines.
