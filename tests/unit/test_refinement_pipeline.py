"""Tests for refinement pipeline."""

from tracevault.refinement.pipeline import refine_document, refine_text


class TestRefineText:
    """Tests for refine_text function."""

    def test_refine_text_returns_tuple(self):
        """Function returns (cleaned_text, metadata) tuple."""
        text = "  Hello   world  "
        cleaned, meta = refine_text(text)
        assert isinstance(cleaned, str)
        assert meta.refinement_method == "rule_based"

    def test_refine_text_preserves_content(self):
        """Content is preserved after refinement."""
        text = "The server uses nginx version 1.20."
        cleaned, _ = refine_text(text)
        assert "nginx" in cleaned
        assert "1.20" in cleaned


class TestRefineDocument:
    """Tests for refine_document function."""

    def test_returns_chunk_list(self):
        """Function returns RefinementResult with chunks."""
        text = "Hello world this is a test."
        result = refine_document("doc_001", text, chunk_size=10)
        assert result.total_chunks > 0
        assert len(result.chunks) == result.total_chunks

    def test_each_chunk_has_raw_and_cleaned(self):
        """Each chunk has both raw_text and cleaned_text."""
        text = "Hello world"
        result = refine_document("doc_001", text)
        for chunk in result.chunks:
            assert chunk.raw_text
            assert chunk.cleaned_text
            assert isinstance(chunk.raw_text, str)
            assert isinstance(chunk.cleaned_text, str)

    def test_each_chunk_has_metadata(self):
        """Each chunk has metadata field."""
        text = "Test"
        result = refine_document("doc_001", text)
        for chunk in result.chunks:
            assert hasattr(chunk, "metadata")
            assert isinstance(chunk.metadata, dict)

    def test_source_raw_content_preserved(self):
        """Original raw content is preserved exactly in chunks."""
        original = "  Hello   World  \n\nTest  "
        result = refine_document("doc_001", original, chunk_size=100)
        # Raw text should be preserved exactly
        assert result.chunks[0].raw_text == original

    def test_no_model_calls_occur(self):
        """Refinement uses rule-based method, not model."""
        text = "Test text"
        result = refine_document("doc_001", text)
        assert result.metadata.refinement_method == "rule_based"
        assert result.metadata.model_name is None

    def test_chunk_ids_deterministic(self):
        """Chunk IDs are deterministic."""
        text = "Hello world test"
        result1 = refine_document("doc_001", text, chunk_size=5)
        result2 = refine_document("doc_001", text, chunk_size=5)
        for c1, c2 in zip(result1.chunks, result2.chunks, strict=True):
            assert c1.chunk_id == c2.chunk_id

    def test_refinement_metadata_attached(self):
        """Overall refinement metadata is attached."""
        text = "Test"
        result = refine_document("doc_001", text)
        assert result.metadata.refinement_method == "rule_based"
        assert result.metadata.no_new_facts_checked is True
        assert result.metadata.source_raw_hash

    def test_statistics_calculated(self):
        """Character statistics are calculated."""
        text = "Hello"
        result = refine_document("doc_001", text)
        assert result.total_raw_chars == 5
        assert result.total_cleaned_chars == 5
        assert result.total_chunks == 1

    def test_empty_document(self):
        """Empty document returns empty result."""
        result = refine_document("doc_001", "")
        assert result.total_chunks == 0
        assert result.chunks == []

    def test_chunk_integrity(self):
        """Each chunk passes integrity verification."""
        text = "Hello world test document"
        result = refine_document("doc_001", text)
        for chunk in result.chunks:
            assert chunk.verify_integrity()

    def test_traceability_metadata(self):
        """Chunks have traceability metadata."""
        text = "Test"
        result = refine_document("doc_001", text)
        for chunk in result.chunks:
            assert chunk.document_id == "doc_001"
            assert chunk.chunk_id.startswith("chunk_doc_001_")
            assert chunk.raw_text_hash
