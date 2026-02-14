"""Tests for OpenCodeWorker."""

import pytest

from app.workers.v1.opencode import OpenCodeWorker


class TestOpenCodeWorker:
    """Tests for OpenCodeWorker."""

    class TestStartConversation:
        """SUT: OpenCodeWorker.start_conversation"""

        @pytest.mark.asyncio
        async def test_raises_not_implemented(self):
            """Should raise NotImplementedError."""
            worker = OpenCodeWorker()
            with pytest.raises(NotImplementedError):
                await worker.start_conversation("/tmp", "hello")

    class TestFetchMessages:
        """SUT: OpenCodeWorker.fetch_messages"""

        @pytest.mark.asyncio
        async def test_raises_not_implemented(self):
            """Should raise NotImplementedError."""
            worker = OpenCodeWorker()
            with pytest.raises(NotImplementedError):
                await worker.fetch_messages("some-id")
