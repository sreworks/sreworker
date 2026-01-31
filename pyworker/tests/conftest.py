"""Pytest fixtures for API testing."""

import os
import shutil
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1 import workers
from app.api import websocket
from app.services.v1.worker_manager import WorkerManager
from app.config import Settings


TEST_DB_DIR = "./data/test"
TEST_DB_PATH = "./data/test/test_worker.db"


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

    # Create test settings
    test_settings = Settings(
        database_path=TEST_DB_PATH,
        log_level="WARNING",
        enable_database=True
    )

    # Create new worker manager
    manager = WorkerManager(test_settings)

    # Set worker manager in API modules
    workers.worker_manager = manager
    websocket.worker_manager = manager

    # Create client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup - close database connection first
    await manager.shutdown()
    if manager.db:
        manager.db.close()
    _clean_test_db()
