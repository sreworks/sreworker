"""Tests for FileManager service."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from app.services.file_manager import FileManager


class TestFileManager:
    """Tests for sync state management (no real awatch)."""

    def test_start_sets_running(self):
        """start() should set _running to True."""
        fm = FileManager()
        fm.start()
        assert fm._running is True
        fm.stop()

    def test_stop_clears_state(self):
        """stop() should clear _running, _watches, and _dir_watches."""
        fm = FileManager()
        fm.start()
        fm._watches["some_path"] = [AsyncMock()]
        fm._dir_watches["some_dir"] = [AsyncMock()]
        fm.stop()
        assert fm._running is False
        assert fm._watches == {}
        assert fm._dir_watches == {}

    def test_watch_registers_callback(self):
        """watch() should add callback to _watches."""
        fm = FileManager()
        # Don't start to avoid creating asyncio tasks
        cb = AsyncMock()
        abs_path = str(Path("/tmp/test.txt").resolve())
        fm._watches[abs_path] = []
        fm._watches[abs_path].append(cb)
        assert len(fm._watches[abs_path]) == 1

    def test_unwatch_removes_callback(self):
        """unwatch() should remove the file from _watches."""
        fm = FileManager()
        cb = AsyncMock()
        abs_path = str(Path("/tmp/testfile.txt").resolve())
        fm._watches[abs_path] = [cb]

        fm.unwatch(abs_path)
        assert abs_path not in fm._watches

    def test_watch_directory_registers(self):
        """watch_directory() should add callback to _dir_watches."""
        fm = FileManager()
        # Don't start - avoid task creation
        cb = AsyncMock()
        abs_dir = str(Path("/tmp/testdir").resolve())
        fm._dir_watches[abs_dir] = []
        fm._dir_watches[abs_dir].append(cb)
        assert len(fm._dir_watches[abs_dir]) == 1

    def test_unwatch_directory_removes(self):
        """unwatch_directory() should remove from _dir_watches."""
        fm = FileManager()
        cb = AsyncMock()
        abs_dir = str(Path("/tmp/testdir2").resolve())
        fm._dir_watches[abs_dir] = [cb]

        fm.unwatch_directory(abs_dir)
        assert abs_dir not in fm._dir_watches

    def test_unwatch_specific_callback(self):
        """unwatch() with specific callback should only remove that one."""
        fm = FileManager()
        cb1 = AsyncMock()
        cb2 = AsyncMock()
        abs_path = str(Path("/tmp/multi_cb.txt").resolve())
        fm._watches[abs_path] = [cb1, cb2]

        fm.unwatch(abs_path, cb1)
        assert len(fm._watches[abs_path]) == 1
        assert fm._watches[abs_path][0] is cb2
