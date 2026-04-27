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

    def test_per_chunk_refinement_metadata_preserved(self):
        """Each chunk carries full refinement metadata from rule_based_refine."""
        text = "Hello world test"
        result = refine_document("doc_001", text, chunk_size=10)
        for chunk in result.chunks:
            meta = chunk.metadata
            # Required proof fields
            assert "refinement_method" in meta
            assert meta["refinement_method"] == "rule_based"
            assert "prompt_version" in meta
            assert "created_at" in meta
            assert "warnings" in meta
            assert "no_new_facts_checked" in meta
            assert meta["no_new_facts_checked"] is True
            assert "source_raw_hash" in meta
            assert "raw_text_length" in meta
            assert "cleaned_text_length" in meta

    def test_chunk_source_raw_hash_matches_chunk_content(self):
        """Chunk metadata source_raw_hash matches chunk raw_text hash."""
        text = "Hello world test document"
        result = refine_document("doc_001", text)
        for chunk in result.chunks:
            expected_hash = chunk.raw_text_hash
            assert chunk.metadata["source_raw_hash"] == expected_hash

    def test_document_stats_equal_original_length_with_overlap(self):
        """Document stats report original length, not sum of overlapped chunks."""
        text = "x" * 1500  # 1500 chars
        result = refine_document("doc_001", text, chunk_size=1000, overlap=200)
        # total_raw_chars should be document length, not sum of chunk lengths
        assert result.total_raw_chars == 1500
        # With overlap, sum of chunk raw lengths would be > 1500
        sum_chunk_lengths = sum(len(c.raw_text) for c in result.chunks)
        assert sum_chunk_lengths > 1500  # Verify overlap actually happened
        assert result.total_raw_chars < sum_chunk_lengths  # Verify we don't double-count

    def test_to_dict_includes_full_metadata(self):
        """to_dict() includes all required metadata fields."""
        text = "Test"
        result = refine_document("doc_001", text)
        d = result.to_dict()
        meta = d["metadata"]
        # Check all required fields
        assert "refinement_method" in meta
        assert "prompt_version" in meta
        assert "model_name" in meta
        assert "created_at" in meta
        assert "warnings" in meta
        assert "no_new_facts_checked" in meta
        assert "source_raw_hash" in meta
        assert "raw_text_length" in meta
        assert "cleaned_text_length" in meta

    def test_cleaned_length_reflects_actual_cleaned_text(self):
        """total_cleaned_chars and metadata.cleaned_text_length reflect actual cleaned length."""
        raw_text = "  Hello   world  "
        result = refine_document("doc_001", raw_text, chunk_size=100)

        # Raw text length is 17
        assert result.total_raw_chars == len(raw_text)
        assert result.metadata.raw_text_length == len(raw_text)

        # Cleaned text is "Hello world" (length 11)
        expected_cleaned = "Hello world"
        assert result.chunks[0].cleaned_text == expected_cleaned
        assert result.total_cleaned_chars == len(expected_cleaned)
        assert result.metadata.cleaned_text_length == len(expected_cleaned)

        # Verify to_dict includes correct values
        d = result.to_dict()
        assert d["metadata"]["cleaned_text_length"] == len(expected_cleaned)
        assert d["total_cleaned_chars"] == len(expected_cleaned)

    def test_overlap_does_not_inflate_cleaned_stats(self):
        """With overlap, total_cleaned_chars equals sum of chunk cleaned lengths."""
        text = "x" * 1500
        result = refine_document("doc_001", text, chunk_size=1000, overlap=200)

        # total_raw_chars is document length
        assert result.total_raw_chars == 1500

        # total_cleaned_chars equals sum of chunk cleaned_text lengths
        sum_cleaned = sum(len(c.cleaned_text) for c in result.chunks)
        assert result.total_cleaned_chars == sum_cleaned
        assert result.metadata.cleaned_text_length == sum_cleaned
