"""Tests for text retrieval policy."""

from tracevault.retrieval.models import CandidateEvidence, TextRetrievalPolicy
from tracevault.retrieval.text_policy import get_search_text


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
        policy = TextRetrievalPolicy.raw_only()
        result = get_search_text(c, policy)
        assert result == "Raw text here"

    def test_cleaned_only_returns_cleaned_text(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.cleaned_only()
        result = get_search_text(c, policy)
        assert result == "Cleaned text here"

    def test_dual_context_returns_both(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.dual_context()
        result = get_search_text(c, policy)
        assert result == "Raw text here Cleaned text here"

    def test_raw_only_does_not_modify_candidate(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.raw_only()
        get_search_text(c, policy)
        assert c.raw_text == "Raw text here"
        assert c.cleaned_text == "Cleaned text here"

    def test_cleaned_only_does_not_modify_candidate(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.cleaned_only()
        get_search_text(c, policy)
        assert c.raw_text == "Raw text here"
        assert c.cleaned_text == "Cleaned text here"

    def test_empty_raw_text(self):
        c = _make_candidate(raw_text="")
        policy = TextRetrievalPolicy.raw_only()
        result = get_search_text(c, policy)
        assert result == ""

    def test_empty_cleaned_text(self):
        c = _make_candidate(cleaned_text="")
        policy = TextRetrievalPolicy.cleaned_only()
        result = get_search_text(c, policy)
        assert result == ""


class TestTextPolicyDoesNotBlankText:
    """text_policy must NOT blank raw_text from results."""

    def test_raw_only_preserves_raw_text(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.raw_only()
        get_search_text(c, policy)
        assert c.raw_text == "Raw text here"
        assert c.cleaned_text == "Cleaned text here"

    def test_cleaned_only_preserves_raw_text(self):
        """CLEANED_ONLY searches cleaned_text only but does NOT blank raw_text."""
        c = _make_candidate()
        policy = TextRetrievalPolicy.cleaned_only()
        get_search_text(c, policy)
        assert c.raw_text == "Raw text here"
        assert c.cleaned_text == "Cleaned text here"

    def test_dual_context_preserves_both(self):
        c = _make_candidate()
        policy = TextRetrievalPolicy.dual_context()
        get_search_text(c, policy)
        assert c.raw_text == "Raw text here"
        assert c.cleaned_text == "Cleaned text here"


class TestNoApplyTextPolicy:
    """apply_text_policy was removed — it blanked raw_text."""

    def test_apply_text_policy_not_exported(self):
        from tracevault.retrieval import text_policy
        assert not hasattr(text_policy, "apply_text_policy")
