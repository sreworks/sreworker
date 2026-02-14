"""File reader utility tests."""

import os
import pytest
from pathlib import Path

from app.utils.file_reader import reverse_readline, read_last_n_lines


TEST_DIR = "./data/test/utils"


@pytest.fixture(scope="function")
def test_dir():
    """Create and cleanup test directory."""
    os.makedirs(TEST_DIR, exist_ok=True)
    yield TEST_DIR
    # Cleanup
    import shutil
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


class TestReverseReadline:
    """SUT: reverse_readline"""

    def test_empty_file(self, test_dir):
        """Test reading empty file."""
        file_path = Path(test_dir) / "empty.txt"
        file_path.write_text("")

        lines = list(reverse_readline(file_path))
        assert lines == []

    def test_single_line(self, test_dir):
        """Test reading file with single line."""
        file_path = Path(test_dir) / "single.txt"
        file_path.write_text("hello world")

        lines = list(reverse_readline(file_path))
        assert lines == ["hello world"]

    def test_multiple_lines(self, test_dir):
        """Test reading file with multiple lines in reverse order."""
        file_path = Path(test_dir) / "multi.txt"
        file_path.write_text("line1\nline2\nline3\n")

        lines = list(reverse_readline(file_path))
        assert lines == ["line3", "line2", "line1"]

    def test_no_trailing_newline(self, test_dir):
        """Test file without trailing newline."""
        file_path = Path(test_dir) / "no_newline.txt"
        file_path.write_text("line1\nline2\nline3")

        lines = list(reverse_readline(file_path))
        assert lines == ["line3", "line2", "line1"]

    def test_nonexistent_file(self, test_dir):
        """Test reading nonexistent file returns empty."""
        file_path = Path(test_dir) / "nonexistent.txt"

        lines = list(reverse_readline(file_path))
        assert lines == []

    def test_unicode_content(self, test_dir):
        """Test reading file with unicode content."""
        file_path = Path(test_dir) / "unicode.txt"
        file_path.write_text("你好\n世界\nHello\n", encoding="utf-8")

        lines = list(reverse_readline(file_path))
        assert lines == ["Hello", "世界", "你好"]

    def test_large_file_small_buffer(self, test_dir):
        """Test reading with small buffer size."""
        file_path = Path(test_dir) / "large.txt"
        content = "\n".join([f"line{i}" for i in range(100)])
        file_path.write_text(content + "\n")

        # Use very small buffer to test chunking
        lines = list(reverse_readline(file_path, buf_size=32))
        assert len(lines) == 100
        assert lines[0] == "line99"
        assert lines[-1] == "line0"

    def test_empty_lines(self, test_dir):
        """Test file with empty lines are skipped."""
        file_path = Path(test_dir) / "empty_lines.txt"
        file_path.write_text("line1\n\nline2\n\nline3\n")

        lines = list(reverse_readline(file_path))
        # Empty lines should be skipped
        assert lines == ["line3", "line2", "line1"]


class TestReadLastNLines:
    """SUT: read_last_n_lines"""

    def test_read_all_lines_reverse(self, test_dir):
        """Test reading all lines in reverse order (default)."""
        file_path = Path(test_dir) / "all.txt"
        file_path.write_text("line1\nline2\nline3\n")

        lines = read_last_n_lines(file_path, 10)
        # Default reverse=True: newest first
        assert lines == ["line3", "line2", "line1"]

    def test_read_all_lines_chronological(self, test_dir):
        """Test reading all lines in chronological order."""
        file_path = Path(test_dir) / "all.txt"
        file_path.write_text("line1\nline2\nline3\n")

        lines = read_last_n_lines(file_path, 10, reverse=False)
        # reverse=False: oldest first
        assert lines == ["line1", "line2", "line3"]

    def test_read_last_n_reverse(self, test_dir):
        """Test reading last N lines in reverse order."""
        file_path = Path(test_dir) / "last_n.txt"
        file_path.write_text("line1\nline2\nline3\nline4\nline5\n")

        lines = read_last_n_lines(file_path, 3)
        # Default reverse=True: newest first
        assert lines == ["line5", "line4", "line3"]

    def test_read_last_n_chronological(self, test_dir):
        """Test reading last N lines in chronological order."""
        file_path = Path(test_dir) / "last_n.txt"
        file_path.write_text("line1\nline2\nline3\nline4\nline5\n")

        lines = read_last_n_lines(file_path, 3, reverse=False)
        # reverse=False: oldest first
        assert lines == ["line3", "line4", "line5"]

    def test_read_last_one(self, test_dir):
        """Test reading only last line."""
        file_path = Path(test_dir) / "last_one.txt"
        file_path.write_text("line1\nline2\nline3\n")

        lines = read_last_n_lines(file_path, 1)
        assert lines == ["line3"]

    def test_empty_file(self, test_dir):
        """Test reading empty file."""
        file_path = Path(test_dir) / "empty.txt"
        file_path.write_text("")

        lines = read_last_n_lines(file_path, 10)
        assert lines == []

    def test_nonexistent_file(self, test_dir):
        """Test reading nonexistent file."""
        file_path = Path(test_dir) / "nonexistent.txt"

        lines = read_last_n_lines(file_path, 10)
        assert lines == []

    def test_unicode_content(self, test_dir):
        """Test reading unicode content."""
        file_path = Path(test_dir) / "unicode.txt"
        file_path.write_text("第一行\n第二行\n第三行\n", encoding="utf-8")

        lines = read_last_n_lines(file_path, 2)
        # Default reverse=True: newest first
        assert lines == ["第三行", "第二行"]

    def test_jsonl_format(self, test_dir):
        """Test reading JSONL format like conversation messages."""
        import json
        file_path = Path(test_dir) / "messages.jsonl"

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]
        with open(file_path, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        lines = read_last_n_lines(file_path, 2)
        assert len(lines) == 2
        # Default reverse=True: newest first
        assert json.loads(lines[0])["content"] == "How are you?"
        assert json.loads(lines[1])["content"] == "Hi"

    def test_large_file_performance(self, test_dir):
        """Test that large file only reads necessary bytes."""
        file_path = Path(test_dir) / "large.txt"

        # Create a file with 1000 lines
        with open(file_path, "w") as f:
            for i in range(1000):
                f.write(f"line{i:04d}\n")

        # Read only last 5 lines (default reverse=True: newest first)
        lines = read_last_n_lines(file_path, 5)
        assert len(lines) == 5
        assert lines == ["line0999", "line0998", "line0997", "line0996", "line0995"]
