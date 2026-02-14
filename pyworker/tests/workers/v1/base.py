"""Tests for BaseWorker abstract class."""

import pytest

from app.workers.v1.base import BaseWorker


class TestBaseWorker:
    """SUT: BaseWorker"""

    def test_cannot_instantiate(self):
        """Directly instantiating BaseWorker should raise TypeError."""
        with pytest.raises(TypeError):
            BaseWorker(env_vars=None, command_params=None)

    def test_subclass_must_implement_all(self):
        """Partial implementation should still raise TypeError."""

        class PartialWorker(BaseWorker):
            async def start_conversation(self, path, message):
                return "id"
            # Missing: achieve_conversation, continue_conversation, fetch_messages

        with pytest.raises(TypeError):
            PartialWorker(env_vars=None, command_params=None)
