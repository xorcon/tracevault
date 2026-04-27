"""Tests for refinement models."""

from tracevault.refinement.models import RefinementMetadata, RefinementResult, TextChunk


class TestTextChunk:
    """Tests for TextChunk dataclass."""

    def test_generate_chunk_id_deterministic(self):
        """Chunk ID is deterministic based on document_id and index."""
        id1 = TextChunk.generate_chunk_id("doc_001", 0)
        id2 = TextChunk.generate_chunk_id("doc_001", 0)
        assert id1 == id2
        assert id1 == "chunk_doc_001_0"

    def test_chunk_id_unique_per_index(self):
        """Different indices produce different IDs."""
        id0 = TextChunk.generate_chunk_id("doc_001", 0)
        id1 = TextChunk.generate_chunk_id("doc_001", 1)
        assert id0 != id1
        assert id0 == "chunk_doc_001_0"
        assert id1 == "chunk_doc_001_1"

    def test_compute_raw_hash(self):
        """Raw hash is computed correctly."""
        text = "Hello world"
        hash1 = TextChunk.compute_raw_hash(text)
        hash2 = TextChunk.compute_raw_hash(text)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_verify_integrity_valid(self):
        """Integrity verification passes for valid chunk."""
        chunk = TextChunk(
            chunk_id="chunk_doc_001_0",
            document_id="doc_001",
            chunk_index=0,
            raw_text="Hello",
            cleaned_text="Hello",
            start_offset=0,
            end_offset=5,
            raw_text_hash=TextChunk.compute_raw_hash("Hello"),
        )
        assert chunk.verify_integrity() is True

    def test_verify_integrity_invalid(self):
        """Integrity verification fails for tampered chunk."""
        chunk = TextChunk(
            chunk_id="chunk_doc_001_0",
            document_id="doc_001",
            chunk_index=0,
            raw_text="Hello",
            cleaned_text="Hello",
            start_offset=0,
            end_offset=5,
            raw_text_hash="invalid_hash",
        )
        assert chunk.verify_integrity() is False

    def test_raw_and_cleaned_stored_separately(self):
        """Raw and cleaned text are separate fields."""
        chunk = TextChunk(
            chunk_id="chunk_doc_001_0",
            document_id="doc_001",
            chunk_index=0,
            raw_text="Raw text",
            cleaned_text="Cleaned text",
            start_offset=0,
            end_offset=9,
            raw_text_hash=TextChunk.compute_raw_hash("Raw text"),
        )
        assert chunk.raw_text == "Raw text"
        assert chunk.cleaned_text == "Cleaned text"
        assert chunk.raw_text != chunk.cleaned_text


class TestRefinementMetadata:
    """Tests for RefinementMetadata dataclass."""

    def test_has_required_fields(self):
        """Metadata has all required fields."""
        meta = RefinementMetadata(
            refinement_method="rule_based",
            prompt_version="v1.0",
            model_name=None,
            created_at="2026-04-27T00:00:00+00:00",
        )
        assert meta.refinement_method == "rule_based"
        assert meta.prompt_version == "v1.0"
        assert meta.model_name is None
        assert meta.warnings == []
        assert meta.no_new_facts_checked is False

    def test_get_current_timestamp(self):
        """Timestamp generation works."""
        ts = RefinementMetadata.get_current_timestamp()
        assert "T" in ts  # ISO 8601 format
        assert len(ts) > 10


class TestRefinementResult:
    """Tests for RefinementResult dataclass."""

    def test_to_dict_serialization(self):
        """Result serializes to dictionary correctly."""
        chunk = TextChunk(
            chunk_id="chunk_doc_001_0",
            document_id="doc_001",
            chunk_index=0,
            raw_text="Hello",
            cleaned_text="Hello",
            start_offset=0,
            end_offset=5,
            raw_text_hash=TextChunk.compute_raw_hash("Hello"),
        )
        meta = RefinementMetadata(
            refinement_method="rule_based",
            prompt_version="v1.0",
            model_name=None,
            created_at="2026-04-27T00:00:00+00:00",
        )
        result = RefinementResult(
            document_id="doc_001",
            chunks=[chunk],
            metadata=meta,
            total_chunks=1,
            total_raw_chars=5,
            total_cleaned_chars=5,
        )
        d = result.to_dict()
        assert d["document_id"] == "doc_001"
        assert len(d["chunks"]) == 1
        assert d["chunks"][0]["raw_text"] == "Hello"
        assert d["metadata"]["refinement_method"] == "rule_based"
