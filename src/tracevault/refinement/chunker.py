"""Deterministic text chunking.

Splits raw text into stable, traceable chunks while preserving the original
raw_text exactly. Chunking is deterministic: same input always produces
same output with identical chunk_ids.

Chunking strategy:
- Character-based splitting with configurable size and overlap
- Preserves raw_text exactly (no cleaning during chunking)
- Generates stable chunk_id: chunk_<document_id>_<index>
- Tracks character offsets for traceability
"""

from dataclasses import dataclass

from tracevault.refinement.models import TextChunk


@dataclass
class ChunkingConfig:
    """Configuration for chunking.

    Attributes:
        chunk_size: Maximum characters per chunk (default: 1000)
        overlap: Characters to overlap between chunks (default: 200)
        split_on_newline: If True, prefer splitting at newlines (default: True)
    """

    chunk_size: int = 1000
    overlap: int = 200
    split_on_newline: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0:
            raise ValueError("overlap must be non-negative")
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be less than chunk_size")


def _find_split_point(text: str, target: int, max_pos: int) -> int:
    """Find optimal split point near target position.

    Tries to split at newline or sentence boundary if split_on_newline is True.
    Never returns a position greater than target (enforces chunk_size as maximum).

    Args:
        text: Full text
        target: Target split position (hard maximum)
        max_pos: Maximum allowed position in text

    Returns:
        Optimal split position (always <= target, always >= 1 to ensure progress)
    """
    # Clamp target to max_pos
    target = min(target, max_pos)

    # Look for newline before target (prefer earlier split, not later)
    # But never go below 1 to ensure we always make progress
    for i in range(target - 1, max(1, target - 50), -1):
        if text[i] == "\n":
            return i

    # Look for sentence boundary before target
    for i in range(target - 1, max(1, target - 50), -1):
        if i > 0 and text[i - 1] in ".!?" and text[i] in " \n":
            return i

    return target


def chunk_text(
    document_id: str,
    raw_text: str,
    chunk_size: int = 1000,
    overlap: int | None = None,
    split_on_newline: bool = True,
) -> list[TextChunk]:
    """Split raw text into deterministic chunks.

    This function preserves the original raw_text exactly. No cleaning,
    normalization, or modification occurs during chunking.

    Args:
        document_id: Parent document identifier
        raw_text: Original text to chunk (preserved exactly)
        chunk_size: Maximum characters per chunk (hard limit)
        overlap: Characters to overlap between consecutive chunks (default: 200, or 0 if chunk_size <= 1)
        split_on_newline: If True, prefer splitting at newlines (default: True)

    Returns:
        List of TextChunk objects with raw_text preserved exactly

    Raises:
        ValueError: If chunk_size <= 0, overlap < 0, or overlap >= chunk_size

    Note:
        When split_on_newline=True, chunks may be shorter than chunk_size if a
        newline or sentence boundary is found before chunk_size. Chunks never
        exceed chunk_size.

    Example:
        >>> chunks = chunk_text("doc_001", "Hello world", chunk_size=5, overlap=0)
        >>> len(chunks)
        3
        >>> chunks[0].raw_text
        'Hello'
    """
    # Set default overlap based on chunk_size
    if overlap is None:
        overlap = 0

    # Validate parameters
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    if not raw_text:
        return []

    chunks: list[TextChunk] = []
    pos = 0
    chunk_index = 0
    text_length = len(raw_text)

    while pos < text_length:
        # Determine end position
        end_pos = min(pos + chunk_size, text_length)

        # Try to find better split point if not at end
        # Ensure we always make progress: new_pos = end_pos - overlap > pos
        # So end_pos must be > pos + overlap
        if end_pos < text_length and split_on_newline:
            candidate = _find_split_point(raw_text, end_pos, text_length)
            # Only use candidate if it ensures we advance past current pos
            if candidate > pos + overlap:
                end_pos = candidate

        # Extract chunk
        chunk_raw = raw_text[pos:end_pos]
        chunk_hash = TextChunk.compute_raw_hash(chunk_raw)
        chunk_id = TextChunk.generate_chunk_id(document_id, chunk_index)

        chunk = TextChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            raw_text=chunk_raw,
            cleaned_text="",  # Will be filled by refiner
            start_offset=pos,
            end_offset=end_pos,
            raw_text_hash=chunk_hash,
            metadata={},
        )
        chunks.append(chunk)

        # Move position with overlap
        pos = end_pos - overlap
        if pos < 0:
            pos = 0
        chunk_index += 1

        # Safety: prevent infinite loop if overlap causes no progress
        if end_pos == text_length:
            break

    return chunks
