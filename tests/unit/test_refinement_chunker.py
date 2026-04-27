"""Tests for deterministic chunker."""

import pytest

from tracevault.refinement.chunker import chunk_text


class TestChunking:
    """Tests for chunk_text function."""

    def test_deterministic_chunking(self):
        """Same input always produces same output."""
        text = "Hello world this is a test document for chunking."
        chunks1 = chunk_text("doc_001", text, chunk_size=10)
        chunks2 = chunk_text("doc_001", text, chunk_size=10)
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2, strict=True):
            assert c1.chunk_id == c2.chunk_id
            assert c1.raw_text == c2.raw_text

    def test_chunk_order_preserved(self):
        """Chunks maintain document order."""
        text = "First second third fourth fifth"
        chunks = chunk_text("doc_001", text, chunk_size=6)
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[0].start_offset < chunks[1].start_offset

    def test_chunk_overlap(self):
        """Chunks overlap by specified amount."""
        text = "0123456789" * 3  # 30 chars
        chunks = chunk_text("doc_001", text, chunk_size=10, overlap=3)
        # First chunk: 0-10, second: 7-17 (overlap of 3)
        assert chunks[0].end_offset == 10
        assert chunks[1].start_offset == 7
        # Check actual overlap in content
        overlap_region = chunks[0].raw_text[-3:] == chunks[1].raw_text[:3]
        assert overlap_region

    def test_empty_text(self):
        """Empty text returns empty list."""
        chunks = chunk_text("doc_001", "")
        assert chunks == []

    def test_short_text(self):
        """Text shorter than chunk_size returns single chunk."""
        text = "Short"
        chunks = chunk_text("doc_001", text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0].raw_text == "Short"

    def test_invalid_chunk_size_zero(self):
        """Zero chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            chunk_text("doc_001", "text", chunk_size=0)

    def test_invalid_chunk_size_negative(self):
        """Negative chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            chunk_text("doc_001", "text", chunk_size=-10)

    def test_invalid_overlap_negative(self):
        """Negative overlap raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            chunk_text("doc_001", "text", chunk_size=100, overlap=-1)

    def test_invalid_overlap_equals_size(self):
        """Overlap equal to chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="less than"):
            chunk_text("doc_001", "text", chunk_size=100, overlap=100)

    def test_invalid_overlap_greater_than_size(self):
        """Overlap greater than chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="less than"):
            chunk_text("doc_001", "text", chunk_size=100, overlap=150)

    def test_raw_text_preserved_exactly(self):
        """Raw text is preserved exactly without modification."""
        original = "  Hello   World  \n\nTest  "
        chunks = chunk_text("doc_001", original, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0].raw_text == original

    def test_chunk_id_format(self):
        """Chunk ID follows expected format."""
        text = "Test text"
        chunks = chunk_text("doc_abc123", text, chunk_size=10)
        assert chunks[0].chunk_id == "chunk_doc_abc123_0"
        if len(chunks) > 1:
            assert chunks[1].chunk_id == "chunk_doc_abc123_1"

    def test_offsets_correct(self):
        """Start and end offsets are correct."""
        text = "Hello world"
        chunks = chunk_text("doc_001", text, chunk_size=5, overlap=0)
        assert chunks[0].start_offset == 0
        assert chunks[0].end_offset == 5
        assert chunks[0].raw_text == "Hello"

    def test_no_infinite_loop_with_overlap(self):
        """Edge case: overlap does not cause infinite loop."""
        text = "abc"
        chunks = chunk_text("doc_001", text, chunk_size=5, overlap=3)
        assert len(chunks) == 1

    def test_hash_computed_correctly(self):
        """Raw text hash is computed."""
        text = "Test"
        chunks = chunk_text("doc_001", text)
        assert chunks[0].raw_text_hash
        assert len(chunks[0].raw_text_hash) == 64  # SHA-256
