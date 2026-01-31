"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .db import DatabaseConnection
from .api.v1 import workers, conversations
from .services import ConversationManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    db_conn = DatabaseConnection("./data/pyworker2.db")
    conv_manager = ConversationManager("./data/conversations")

    # Inject dependencies into routers
    workers.db_conn = db_conn
    conversations.db_conn = db_conn
    conversations.conv_manager = conv_manager

    yield

    # Shutdown
    db_conn.close()


app = FastAPI(
    title="PyWorker2 API",
    description="Worker and Conversation management API",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(workers.router)
app.include_router(conversations.router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7788)
