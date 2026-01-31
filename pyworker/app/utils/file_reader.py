"""File reading utilities."""

from pathlib import Path
from typing import Iterator, Union


def reverse_readline(
    file_path: Union[str, Path],
    buf_size: int = 8192
) -> Iterator[str]:
    """
    Read a file line by line in reverse order (from end to beginning).

    Memory efficient - only loads buf_size bytes at a time.

    Args:
        file_path: Path to the file
        buf_size: Size of buffer for reading chunks (default 8KB)

    Yields:
        Lines from the file in reverse order (newest first)
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return

    with open(file_path, 'rb') as f:
        # Move to end of file
        f.seek(0, 2)
        position = f.tell()

        if position == 0:
            return

        buffer = b''

        while position > 0:
            # Calculate how much to read
            read_size = min(buf_size, position)
            position -= read_size

            # Seek and read chunk
            f.seek(position)
            chunk = f.read(read_size)

            # Prepend to buffer
            buffer = chunk + buffer

            # Split into lines
            lines = buffer.split(b'\n')

            # First element may be incomplete line, keep it in buffer
            buffer = lines[0]

            # Yield complete lines in reverse order
            for line in reversed(lines[1:]):
                if line:
                    try:
                        yield line.decode('utf-8')
                    except UnicodeDecodeError:
                        # Handle partial UTF-8 character at chunk boundary
                        # Put it back to buffer and continue
                        buffer = buffer + b'\n' + line

        # Don't forget the first line (remaining buffer)
        if buffer:
            try:
                yield buffer.decode('utf-8')
            except UnicodeDecodeError:
                pass


def read_last_n_lines(
    file_path: Union[str, Path],
    n: int,
    buf_size: int = 8192,
    reverse: bool = True
) -> list[str]:
    """
    Read the last N lines from a file efficiently.

    Args:
        file_path: Path to the file
        n: Number of lines to read
        buf_size: Size of buffer for reading chunks
        reverse: If True, return newest first; if False, return oldest first

    Returns:
        List of last N lines
    """
    lines = []
    for line in reverse_readline(file_path, buf_size):
        lines.append(line)
        if len(lines) >= n:
            break

    # reverse=True: newest first (as read from file end)
    # reverse=False: oldest first (chronological order)
    if not reverse:
        lines.reverse()

    return lines
