"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .config import settings
from .services.v1.worker_manager import WorkerManager
from .adapters.v1.registry import register_default_adapters
from .utils.logger import init_app_logger
from .api.v1 import workers
from .api import websocket


# Initialize logger
logger = init_app_logger(settings)

# Global worker manager instance
worker_manager_instance: WorkerManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("=" * 70)
    logger.info("Starting AI Code Worker Manager...")
    logger.info("=" * 70)

    # Print server configuration
    logger.info("")
    logger.info("📡 Server Configuration:")
    logger.info(f"  Host: {settings.host}")
    logger.info(f"  Port: {settings.port}")
    logger.info(f"  Debug: {settings.debug}")
    logger.info(f"  Log Level: {settings.log_level}")
    logger.info(f"  Log File: {settings.log_file}")

    # Print worker configuration
    logger.info("")
    logger.info("⚙️  Worker Configuration:")
    logger.info(f"  Max Workers: {settings.max_workers}")
    logger.info(f"  Worker Timeout: {settings.worker_timeout}s")
    logger.info(f"  Workers Base Dir: {settings.workers_base_dir}")

    # Print AI CLI configuration
    logger.info("")
    logger.info("🤖 AI CLI Configuration:")
    logger.info(f"  Default AI CLI: {settings.default_ai_cli}")
    logger.info(f"  Enabled AI CLIs: {', '.join(settings.get_enabled_ai_clis())}")

    # Print Claude configuration
    if "claude" in settings.get_enabled_ai_clis():
        logger.info("")
        logger.info("  🔵 Claude Code:")
        logger.info(f"    Binary: {settings.claude_binary}")
        logger.info(f"    Model: {settings.claude_model}")

        # Check API key from config
        if settings.claude_api_key:
            masked_key = settings.claude_api_key[:8] + "..." + settings.claude_api_key[-4:] if len(settings.claude_api_key) > 12 else "***"
            logger.info(f"    API Key (from .env): {masked_key}")
        else:
            logger.info(f"    API Key (from .env): Not set")

        # Check API key from environment
        import os
        env_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_api_key:
            masked_env_key = env_api_key[:8] + "..." + env_api_key[-4:] if len(env_api_key) > 12 else "***"
            logger.info(f"    API Key (from env): {masked_env_key} ✅")
        else:
            logger.info(f"    API Key (from env): Not set")

    # Print OpenCode configuration
    if "opencode" in settings.get_enabled_ai_clis():
        logger.info("")
        logger.info("  🟢 OpenCode:")
        logger.info(f"    Binary: {settings.opencode_binary}")
        logger.info(f"    Model: {settings.opencode_model}")
        logger.info(f"    API Base: {settings.opencode_api_base}")

        # Check API key from config
        if settings.opencode_api_key:
            masked_key = settings.opencode_api_key[:8] + "..." + settings.opencode_api_key[-4:] if len(settings.opencode_api_key) > 12 else "***"
            logger.info(f"    API Key (from .env): {masked_key}")
        else:
            logger.info(f"    API Key (from .env): Not set")

        # Check API key from environment
        import os
        env_api_key = os.environ.get("OPENCODE_API_KEY")
        if env_api_key:
            masked_env_key = env_api_key[:8] + "..." + env_api_key[-4:] if len(env_api_key) > 12 else "***"
            logger.info(f"    API Key (from env): {masked_env_key} ✅")
        else:
            logger.info(f"    API Key (from env): Not set")

    # Register default adapters
    logger.info("")
    logger.info("🔌 Registering Adapters...")
    register_default_adapters(settings)
    logger.info(f"  Registered: {', '.join(settings.get_enabled_ai_clis())}")

    # Initialize worker manager
    logger.info("")
    logger.info("🚀 Initializing Worker Manager...")
    global worker_manager_instance
    worker_manager_instance = WorkerManager(settings)

    # Set worker manager in API modules
    workers.worker_manager = worker_manager_instance
    websocket.worker_manager = worker_manager_instance

    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ AI Code Worker Manager started successfully!")
    logger.info(f"📍 Access at: http://{settings.host}:{settings.port}")
    logger.info(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 70)

    yield

    # Shutdown
    logger.info("")
    logger.info("=" * 70)
    logger.info("Shutting down AI Code Worker Manager...")
    logger.info("=" * 70)

    # Shutdown all workers
    if worker_manager_instance:
        await worker_manager_instance.shutdown()

    logger.info("✅ AI Code Worker Manager shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="AI Code Worker Manager",
    description="A unified manager for multiple AI Code CLI workers",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(workers.router)
app.include_router(websocket.router)

# Get static files directory path
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def read_root():
    """
    Serve the main HTML page.

    Returns:
        HTML file response
    """
    index_path = os.path.join(STATIC_DIR, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "AI Code Worker Manager API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health"
        }


@app.get("/health")
async def health():
    """
    Simple health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "AI Code Worker Manager"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
