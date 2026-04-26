"""File loading utilities.

Provides safe file loading with UTF-8 decoding and raw text preservation.
"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}


def is_supported_file(file_path: Path) -> bool:
    """Check if file has supported extension.

    Args:
        file_path: Path to check.

    Returns:
        True if extension is supported.
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def load_file(file_path: Path, encoding: str = "utf-8") -> tuple[str, int]:
    """Load file content preserving raw text.

    Args:
        file_path: Path to file.
        encoding: Text encoding (default: utf-8).

    Returns:
        Tuple of (raw_content, size_bytes).

    Raises:
        FileNotFoundError: If file does not exist.
        UnicodeDecodeError: If file cannot be decoded.
        IsADirectoryError: If path is a directory.
        PermissionError: If file cannot be accessed.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory: {file_path}")

    # Read as binary first to get exact size, then decode
    raw_bytes = file_path.read_bytes()
    size_bytes = len(raw_bytes)

    # Decode to text
    try:
        content = raw_bytes.decode(encoding)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding, e.object, e.start, e.end,
            f"Cannot decode file {file_path} as {encoding}"
        ) from e

    return content, size_bytes


def get_source_type(file_path: Path) -> str:
    """Get source type from file extension.

    Args:
        file_path: Path to file.

    Returns:
        Source type string (txt, md, markdown).
    """
    ext = file_path.suffix.lower()
    if ext in {".md", ".markdown"}:
        return "md"
    return "txt"
