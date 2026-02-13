"""Pytest fixtures for API testing."""

import os
import shutil
import pytest
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1 import workers, conversations
from app.db import DatabaseConnection
from app.services import ConversationManager
from app.services.file_manager import FileManager
from app.workers.v1.claude import ClaudeCodeWorker


TEST_DB_DIR = "./data/test"
TEST_DB_PATH = "./data/test/test_pyworker2.db"
TEST_CONV_PATH = "./data/test/conversations"


def _clean_test_db():
    """Clean test database files."""
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)
    os.makedirs(TEST_DB_DIR, exist_ok=True)


@pytest.fixture(scope="function")
async def client():
    """Create async HTTP client with fresh database for each test."""
    # Clean database before test
    _clean_test_db()

    # Create database connection, conversation manager, and file manager
    db_conn = DatabaseConnection(TEST_DB_PATH)
    conv_manager = ConversationManager(TEST_CONV_PATH)
    fm = FileManager()
    fm.start()

    # Inject dependencies into routers
    workers.db_conn = db_conn
    conversations.db_conn = db_conn
    conversations.conv_manager = conv_manager
    conversations.file_manager = fm

    # Create a test app without lifespan (to avoid conflicts)
    test_app = FastAPI(title="PyWorker2 Test")
    test_app.include_router(workers.router)
    test_app.include_router(conversations.router)

    @test_app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    # Create client
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    ClaudeCodeWorker.stop_watching()
    fm.stop()
    db_conn.close()
    _clean_test_db()
