"""Tests for retrieval data models."""

import dataclasses

import pytest

from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalScore,
    RetrievalTrace,
    TextRetrievalPolicy,
)


def _make_candidate(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
    chunk_index=0,
    source_path="docs/test.md",
    source_type="md",
    raw_text="Hello world",
    cleaned_text="Hello world",
    raw_text_hash="abc123",
    cleaned_text_hash=None,
    metadata=None,
) -> CandidateEvidence:
    return CandidateEvidence(
        document_id=document_id,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        source_path=source_path,
        source_type=source_type,
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        raw_text_hash=raw_text_hash,
        cleaned_text_hash=cleaned_text_hash,
        metadata=metadata or {},
    )


class TestTextRetrievalPolicy:
    """Tests for TextRetrievalPolicy."""

    def test_raw_only_mode(self):
        policy = TextRetrievalPolicy.raw_only()
        assert policy.mode == "RAW_ONLY"
        assert policy.uses_raw() is True
        assert policy.uses_cleaned() is False
        assert policy.preserves_raw() is True
        assert policy.preserves_cleaned() is False

    def test_cleaned_only_mode(self):
        policy = TextRetrievalPolicy.cleaned_only()
        assert policy.mode == "CLEANED_ONLY"
        assert policy.uses_raw() is False
        assert policy.uses_cleaned() is True
        assert policy.preserves_raw() is False
        assert policy.preserves_cleaned() is True

    def test_dual_context_mode(self):
        policy = TextRetrievalPolicy.dual_context()
        assert policy.mode == "DUAL_CONTEXT"
        assert policy.uses_raw() is True
        assert policy.uses_cleaned() is True
        assert policy.preserves_raw() is True
        assert policy.preserves_cleaned() is True

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            TextRetrievalPolicy(mode="INVALID")

    def test_policy_is_frozen(self):
        policy = TextRetrievalPolicy.dual_context()
        with pytest.raises(dataclasses.FrozenInstanceError):
            policy.mode = "RAW_ONLY"  # type: ignore


class TestMetadataFilter:
    """Tests for MetadataFilter."""

    def test_empty_filter(self):
        f = MetadataFilter()
        assert f.is_empty() is True

    def test_filter_with_document_id(self):
        f = MetadataFilter(document_id="doc_001")
        assert f.is_empty() is False

    def test_filter_matches_document_id(self):
        f = MetadataFilter(document_id="doc_001")
        c = _make_candidate(document_id="doc_001")
        assert f.matches(c) is True

    def test_filter_rejects_wrong_document_id(self):
        f = MetadataFilter(document_id="doc_001")
        c = _make_candidate(document_id="doc_002")
        assert f.matches(c) is False

    def test_filter_matches_source_path(self):
        f = MetadataFilter(source_path="docs/test.md")
        c = _make_candidate(source_path="docs/test.md")
        assert f.matches(c) is True

    def test_filter_rejects_wrong_source_path(self):
        f = MetadataFilter(source_path="docs/test.md")
        c = _make_candidate(source_path="docs/other.md")
        assert f.matches(c) is False

    def test_filter_matches_source_type(self):
        f = MetadataFilter(source_type="md")
        c = _make_candidate(source_type="md")
        assert f.matches(c) is True

    def test_filter_matches_key_value(self):
        f = MetadataFilter(key_value={"env": "prod"})
        c = _make_candidate(metadata={"env": "prod"})
        assert f.matches(c) is True

    def test_filter_rejects_wrong_key_value(self):
        f = MetadataFilter(key_value={"env": "prod"})
        c = _make_candidate(metadata={"env": "dev"})
        assert f.matches(c) is False

    def test_filter_missing_key_fails(self):
        f = MetadataFilter(key_value={"env": "prod"})
        c = _make_candidate(metadata={})
        assert f.matches(c) is False

    def test_combined_filter_all_match(self):
        f = MetadataFilter(
            document_id="doc_001",
            source_path="docs/test.md",
            source_type="md",
            key_value={"env": "prod"},
        )
        c = _make_candidate(
            document_id="doc_001",
            source_path="docs/test.md",
            source_type="md",
            metadata={"env": "prod"},
        )
        assert f.matches(c) is True

    def test_combined_filter_one_fails(self):
        f = MetadataFilter(
            document_id="doc_001",
            source_type="md",
        )
        c = _make_candidate(
            document_id="doc_001",
            source_type="txt",
        )
        assert f.matches(c) is False

    def test_to_dict(self):
        f = MetadataFilter(
            document_id="doc_001",
            source_path="docs/test.md",
            key_value={"env": "prod"},
        )
        d = f.to_dict()
        assert d["document_id"] == "doc_001"
        assert d["source_path"] == "docs/test.md"
        assert d["key_value"]["env"] == "prod"


class TestRetrievalScore:
    """Tests for RetrievalScore."""

    def test_default_scores(self):
        s = RetrievalScore()
        assert s.keyword_score == 0.0
        assert s.vector_score == 0.0
        assert s.hybrid_score == 0.0
        assert s.alpha == 0.5

    def test_to_dict(self):
        s = RetrievalScore(
            keyword_score=0.8,
            vector_score=0.6,
            hybrid_score=0.7,
            alpha=0.5,
        )
        d = s.to_dict()
        assert d["keyword_score"] == 0.8
        assert d["vector_score"] == 0.6
        assert d["hybrid_score"] == 0.7
        assert d["alpha"] == 0.5


class TestRetrievalTrace:
    """Tests for RetrievalTrace."""

    def test_required_fields(self):
        t = RetrievalTrace(
            document_id="doc_001",
            chunk_id="chunk_doc_001_0",
            source_path="docs/test.md",
            raw_text_hash="abc123",
        )
        assert t.document_id == "doc_001"
        assert t.chunk_id == "chunk_doc_001_0"
        assert t.source_path == "docs/test.md"
        assert t.raw_text_hash == "abc123"
        assert t.cleaned_text_hash is None
        assert t.retrieval_source == ""
        assert t.matched_fields == []
        assert t.applied_filters == []

    def test_to_dict(self):
        t = RetrievalTrace(
            document_id="doc_001",
            chunk_id="chunk_doc_001_0",
            source_path="docs/test.md",
            raw_text_hash="abc123",
            cleaned_text_hash="def456",
            retrieval_source="hybrid",
            matched_fields=["raw_text", "cleaned_text"],
            applied_filters=["document_id=doc_001"],
        )
        d = t.to_dict()
        assert d["document_id"] == "doc_001"
        assert d["retrieval_source"] == "hybrid"
        assert d["matched_fields"] == ["raw_text", "cleaned_text"]


class TestCandidateEvidence:
    """Tests for CandidateEvidence."""

    def test_to_dict(self):
        c = _make_candidate()
        d = c.to_dict()
        assert d["document_id"] == "doc_001"
        assert d["chunk_id"] == "chunk_doc_001_0"
        assert d["raw_text"] == "Hello world"
        assert d["cleaned_text"] == "Hello world"
        assert d["raw_text_hash"] == "abc123"


class TestRetrievalResult:
    """Tests for RetrievalResult."""

    def test_properties(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        assert r.document_id == "doc_001"
        assert r.chunk_id == "chunk_doc_001_0"
        assert r.source_path == "docs/test.md"
        assert r.raw_text_hash == "abc123"
        assert r.cleaned_text_hash is None

    def test_to_dict(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        d = r.to_dict()
        assert d["rank"] == 1
        assert d["retrieval_run_id"] == "run_001"
        assert d["query_hash"] == "qhash"


class TestRetrievalRequest:
    """Tests for RetrievalRequest."""

    def test_default_text_policy(self):
        req = RetrievalRequest(query="test")
        assert req.text_policy.mode == "DUAL_CONTEXT"

    def test_empty_query_validation(self):
        req = RetrievalRequest(query="")
        errors = req.validate()
        assert "Query must not be empty" in errors

    def test_whitespace_query_validation(self):
        req = RetrievalRequest(query="   ")
        errors = req.validate()
        assert "Query must not be empty" in errors

    def test_invalid_top_k(self):
        req = RetrievalRequest(query="test", top_k=0)
        errors = req.validate()
        assert "top_k must be >= 1" in errors

    def test_negative_top_k(self):
        req = RetrievalRequest(query="test", top_k=-1)
        errors = req.validate()
        assert "top_k must be >= 1" in errors

    def test_alpha_too_low(self):
        req = RetrievalRequest(query="test", alpha=-0.1)
        errors = req.validate()
        assert "alpha must be between 0.0 and 1.0" in errors

    def test_alpha_too_high(self):
        req = RetrievalRequest(query="test", alpha=1.1)
        errors = req.validate()
        assert "alpha must be between 0.0 and 1.0" in errors

    def test_valid_request(self):
        req = RetrievalRequest(query="test", top_k=5, alpha=0.5)
        errors = req.validate()
        assert errors == []

    def test_alpha_boundary_zero(self):
        req = RetrievalRequest(query="test", alpha=0.0)
        errors = req.validate()
        assert errors == []

    def test_alpha_boundary_one(self):
        req = RetrievalRequest(query="test", alpha=1.0)
        errors = req.validate()
        assert errors == []

    def test_compute_query_hash(self):
        h1 = RetrievalRequest.compute_query_hash("test query")
        h2 = RetrievalRequest.compute_query_hash("test query")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_compute_query_hash_different(self):
        h1 = RetrievalRequest.compute_query_hash("query a")
        h2 = RetrievalRequest.compute_query_hash("query b")
        assert h1 != h2


class TestRetrievalResponse:
    """Tests for RetrievalResponse."""

    def test_to_dict(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        resp = RetrievalResponse(
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            results=[r],
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            applied_filters="",
        )
        d = resp.to_dict()
        assert d["retrieval_run_id"] == "run_001"
        assert d["query"] == "test"
        assert d["total_candidates"] == 1
        assert d["alpha"] == 0.5
        assert d["text_policy"] == "DUAL_CONTEXT"
        assert len(d["results"]) == 1


class TestModelTraceability:
    """Tests that models preserve traceability fields."""

    def test_candidate_preserves_document_id_chunk_id(self):
        c = _make_candidate(
            document_id="doc_abc",
            chunk_id="chunk_doc_abc_5",
            source_path="docs/deep/file.md",
            raw_text_hash="sha256hash",
        )
        d = c.to_dict()
        assert d["document_id"] == "doc_abc"
        assert d["chunk_id"] == "chunk_doc_abc_5"
        assert d["source_path"] == "docs/deep/file.md"
        assert d["raw_text_hash"] == "sha256hash"

    def test_result_preserves_traceability(self):
        c = _make_candidate(
            document_id="doc_xyz",
            chunk_id="chunk_doc_xyz_3",
            source_path="docs/file.md",
            raw_text_hash="hash123",
            cleaned_text_hash="hash456",
        )
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        d = r.to_dict()
        assert d["candidate"]["document_id"] == "doc_xyz"
        assert d["candidate"]["chunk_id"] == "chunk_doc_xyz_3"
        assert d["candidate"]["raw_text_hash"] == "hash123"
        assert d["candidate"]["cleaned_text_hash"] == "hash456"

    def test_response_preserves_audit_metadata(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        resp = RetrievalResponse(
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            results=[r],
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            applied_filters="document_id=doc_001",
        )
        d = resp.to_dict()
        assert d["retrieval_run_id"] == "run_001"
        assert d["query_hash"] == "qhash"
        assert d["applied_filters"] == "document_id=doc_001"


class TestRetrievalDoesNotModifyText:
    """Tests that retrieval models do not modify raw_text or cleaned_text."""

    def test_candidate_does_not_modify_raw_text(self):
        original_raw = "Original raw text"
        c = _make_candidate(raw_text=original_raw)
        assert c.raw_text == original_raw

    def test_candidate_does_not_modify_cleaned_text(self):
        original_cleaned = "Original cleaned text"
        c = _make_candidate(cleaned_text=original_cleaned)
        assert c.cleaned_text == original_cleaned

    def test_candidate_does_not_generate_answer(self):
        c = _make_candidate()
        assert not hasattr(c, "answer")
        assert "answer" not in c.to_dict()

    def test_result_does_not_generate_answer(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        assert not hasattr(r, "answer")
        assert "answer" not in r.to_dict()

    def test_response_does_not_generate_answer(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        resp = RetrievalResponse(
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            results=[r],
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
        )
        d = resp.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "llm" not in d
