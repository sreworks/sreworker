"""Tests for OpenCodeWorker."""

import pytest

from app.workers.v1.opencode import OpenCodeWorker


class TestOpenCodeWorker:
    """Tests for OpenCodeWorker stub."""

    @pytest.mark.asyncio
    async def test_start_conversation_raises(self):
        """start_conversation should raise NotImplementedError."""
        worker = OpenCodeWorker()
        with pytest.raises(NotImplementedError):
            await worker.start_conversation("/tmp", "hello")

    @pytest.mark.asyncio
    async def test_fetch_messages_raises(self):
        """fetch_messages should raise NotImplementedError."""
        worker = OpenCodeWorker()
        with pytest.raises(NotImplementedError):
            await worker.fetch_messages("some-id")
