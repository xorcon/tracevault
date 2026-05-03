"""Tests for retrieval text policy."""

from tracevault.retrieval.models import CandidateEvidence, TextRetrievalPolicy
from tracevault.retrieval.text_policy import apply_text_policy, get_search_text


def _make_candidate(
    raw_text="Raw text here",
    cleaned_text="Cleaned text here",
) -> CandidateEvidence:
    return CandidateEvidence(
        document_id="doc_001",
        chunk_id="chunk_doc_001_0",
        chunk_index=0,
        source_path="docs/test.md",
        source_type="md",
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        raw_text_hash="abc123",
    )


class TestGetSearchText:
    def test_raw_only_returns_raw_text(self):
        c = _make_candidate()
        text = get_search_text(c, TextRetrievalPolicy.raw_only())
        assert text == "Raw text here"

    def test_cleaned_only_returns_cleaned_text(self):
        c = _make_candidate()
        text = get_search_text(c, TextRetrievalPolicy.cleaned_only())
        assert text == "Cleaned text here"

    def test_dual_context_returns_both(self):
        c = _make_candidate()
        text = get_search_text(c, TextRetrievalPolicy.dual_context())
        assert text == "Raw text here Cleaned text here"


class TestApplyTextPolicy:
    def test_raw_only_preserves_raw_clears_cleaned(self):
        c = _make_candidate()
        result = apply_text_policy([c], TextRetrievalPolicy.raw_only())
        assert len(result) == 1
        assert result[0].raw_text == "Raw text here"
        assert result[0].cleaned_text == ""

    def test_cleaned_only_preserves_cleaned_clears_raw(self):
        c = _make_candidate()
        result = apply_text_policy([c], TextRetrievalPolicy.cleaned_only())
        assert len(result) == 1
        assert result[0].raw_text == ""
        assert result[0].cleaned_text == "Cleaned text here"

    def test_dual_context_preserves_both(self):
        c = _make_candidate()
        result = apply_text_policy([c], TextRetrievalPolicy.dual_context())
        assert len(result) == 1
        assert result[0].raw_text == "Raw text here"
        assert result[0].cleaned_text == "Cleaned text here"

    def test_does_not_modify_original(self):
        c = _make_candidate()
        original_raw = c.raw_text
        original_cleaned = c.cleaned_text
        apply_text_policy([c], TextRetrievalPolicy.raw_only())
        assert c.raw_text == original_raw
        assert c.cleaned_text == original_cleaned

    def test_preserves_hashes(self):
        c = _make_candidate()
        result = apply_text_policy([c], TextRetrievalPolicy.raw_only())
        assert result[0].raw_text_hash == "abc123"

    def test_empty_input(self):
        result = apply_text_policy([], TextRetrievalPolicy.dual_context())
        assert len(result) == 0

    def test_multiple_candidates(self):
        c1 = _make_candidate(raw_text="First", cleaned_text="first")
        c2 = _make_candidate(raw_text="Second", cleaned_text="second")
        result = apply_text_policy([c1, c2], TextRetrievalPolicy.dual_context())
        assert len(result) == 2
        assert result[0].raw_text == "First"
        assert result[1].raw_text == "Second"
