"""Content hashing utilities.

Provides SHA-256 hashing for document content verification.
"""

import hashlib
from pathlib import Path


def compute_content_hash(content: str | bytes) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: Text or bytes to hash.

    Returns:
        Hexadecimal SHA-256 hash string.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents.

    Args:
        file_path: Path to file.

    Returns:
        Hexadecimal SHA-256 hash string.

    Raises:
        FileNotFoundError: If file does not exist.
        IOError: If file cannot be read.
    """
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_hash(content: str | bytes, expected_hash: str) -> bool:
    """Verify content matches expected hash.

    Args:
        content: Content to verify.
        expected_hash: Expected SHA-256 hash.

    Returns:
        True if content hash matches expected.
    """
    return compute_content_hash(content) == expected_hash
