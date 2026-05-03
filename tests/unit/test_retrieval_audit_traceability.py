"""Tests for retrieval audit traceability."""

from tracevault.retrieval.audit import (
    build_response,
    build_trace,
    compute_cleaned_text_hash,
    compute_query_hash,
    generate_run_id,
    rank_candidates,
)
from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalRequest,
    RetrievalResult,
    TextRetrievalPolicy,
)
from tracevault.retrieval.pipeline import HybridRetrievalPipeline
from tracevault.retrieval.vector import InMemoryVectorRetrieverPlaceholder


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


class TestGenerateRunId:
    def test_run_id_format(self):
        run_id = generate_run_id()
        assert run_id.startswith("run_")
        assert len(run_id) == 20

    def test_run_id_unique(self):
        ids = {generate_run_id() for _ in range(10)}
        assert len(ids) == 10


class TestComputeQueryHash:
    def test_deterministic(self):
        h1 = compute_query_hash("test query")
        h2 = compute_query_hash("test query")
        assert h1 == h2

    def test_different_query_different_hash(self):
        h1 = compute_query_hash("query a")
        h2 = compute_query_hash("query b")
        assert h1 != h2

    def test_sha256_length(self):
        h = compute_query_hash("test")
        assert len(h) == 64


class TestComputeCleanedTextHash:
    def test_deterministic(self):
        h1 = compute_cleaned_text_hash("cleaned text")
        h2 = compute_cleaned_text_hash("cleaned text")
        assert h1 == h2

    def test_sha256_length(self):
        h = compute_cleaned_text_hash("test")
        assert len(h) == 64


class TestBuildTrace:
    def test_trace_has_required_fields(self):
        c = _make_candidate()
        trace = build_trace(c, "keyword", ["raw_text"], None)
        assert trace.document_id == "doc_001"
        assert trace.chunk_id == "chunk_doc_001_0"
        assert trace.source_path == "docs/test.md"
        assert trace.raw_text_hash == "abc123"
        assert trace.retrieval_source == "keyword"
        assert trace.matched_fields == ["raw_text"]

    def test_trace_with_filters(self):
        c = _make_candidate()
        f = MetadataFilter(document_id="doc_001")
        trace = build_trace(c, "hybrid", ["raw_text", "cleaned_text"], f)
        assert "document_id=doc_001" in trace.applied_filters

    def test_trace_without_filters(self):
        c = _make_candidate()
        trace = build_trace(c, "keyword", ["raw_text"], None)
        assert trace.applied_filters == []


class TestRankCandidates:
    def test_rank_is_1_based(self):
        c = _make_candidate()
        results = rank_candidates([c], "run_001", "qhash", 5)
        assert results[0].rank == 1

    def test_top_k_limits(self):
        corpus = [
            _make_candidate(chunk_id=f"chunk_doc_001_{i}", chunk_index=i)
            for i in range(10)
        ]
        results = rank_candidates(corpus, "run_001", "qhash", 3)
        assert len(results) == 3

    def test_run_id_and_query_hash(self):
        c = _make_candidate()
        results = rank_candidates([c], "run_001", "qhash", 5)
        assert results[0].retrieval_run_id == "run_001"
        assert results[0].query_hash == "qhash"


class TestBuildResponse:
    def test_response_fields(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        resp = build_response(
            results=[r],
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=None,
        )
        assert resp.retrieval_run_id == "run_001"
        assert resp.query == "test"
        assert resp.total_candidates == 1
        assert resp.alpha == 0.5
        assert resp.text_policy.mode == "DUAL_CONTEXT"

    def test_response_with_filters(self):
        c = _make_candidate()
        r = RetrievalResult(
            rank=1,
            candidate=c,
            retrieval_run_id="run_001",
            query_hash="qhash",
        )
        f = MetadataFilter(document_id="doc_001")
        resp = build_response(
            results=[r],
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=f,
        )
        assert "document_id=doc_001" in resp.applied_filters


class TestEndToEndTraceability:
    def _make_pipeline(self, corpus):
        kw = InMemoryKeywordRetriever(corpus)
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        return HybridRetrievalPipeline(kw, vec)

    def test_full_traceability_chain(self):
        corpus = [
            _make_candidate(
                document_id="doc_abc123",
                chunk_id="chunk_doc_abc123_0",
                chunk_index=0,
                source_path="docs/knowledge.md",
                source_type="md",
                raw_text="The enterprise architecture includes hybrid cloud patterns",
                cleaned_text="Enterprise architecture includes hybrid cloud patterns",
                raw_text_hash="sha256raw123",
                cleaned_text_hash="sha256clean456",
                metadata={"refinement_method": "rule_based"},
            ),
        ]
        pipeline = self._make_pipeline(corpus)
        req = RetrievalRequest(query="enterprise architecture", top_k=5)
        resp = pipeline.retrieve(req)

        assert resp.retrieval_run_id.startswith("run_")
        assert len(resp.query_hash) == 64
        assert resp.query == "enterprise architecture"

        assert len(resp.results) >= 1
        r = resp.results[0]
        assert r.document_id == "doc_abc123"
        assert r.chunk_id == "chunk_doc_abc123_0"
        assert r.source_path == "docs/knowledge.md"
        assert r.raw_text_hash == "sha256raw123"
        assert r.cleaned_text_hash == "sha256clean456"

        c = r.candidate
        assert c.document_id == "doc_abc123"
        assert c.chunk_id == "chunk_doc_abc123_0"
        assert c.source_path == "docs/knowledge.md"
        assert c.raw_text_hash == "sha256raw123"
        assert c.cleaned_text_hash == "sha256clean456"
        assert c.raw_text == "The enterprise architecture includes hybrid cloud patterns"
        assert c.cleaned_text == "Enterprise architecture includes hybrid cloud patterns"

        t = c.trace
        assert t.document_id == "doc_abc123"
        assert t.chunk_id == "chunk_doc_abc123_0"
        assert t.source_path == "docs/knowledge.md"
        assert t.raw_text_hash == "sha256raw123"

    def test_serialization_preserves_audit_metadata(self):
        corpus = [
            _make_candidate(
                document_id="doc_001",
                chunk_id="chunk_doc_001_0",
                source_path="docs/test.md",
                raw_text_hash="hash123",
                cleaned_text_hash="hash456",
                raw_text="Python code",
                cleaned_text="Python code",
            ),
        ]
        pipeline = self._make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)

        d = resp.to_dict()
        assert d["retrieval_run_id"] == resp.retrieval_run_id
        assert d["query_hash"] == resp.query_hash
        assert d["alpha"] == resp.alpha
        assert d["text_policy"] == resp.text_policy.mode

        if d["results"]:
            r = d["results"][0]
            assert r["candidate"]["document_id"] == "doc_001"
            assert r["candidate"]["chunk_id"] == "chunk_doc_001_0"
            assert r["candidate"]["source_path"] == "docs/test.md"
            assert r["candidate"]["raw_text_hash"] == "hash123"
            assert r["candidate"]["cleaned_text_hash"] == "hash456"
            assert r["retrieval_run_id"] == resp.retrieval_run_id
            assert r["query_hash"] == resp.query_hash

    def test_raw_text_not_modified(self):
        original_raw = "Original raw text that must not change"
        corpus = [
            _make_candidate(
                raw_text=original_raw,
                cleaned_text="Cleaned version",
            ),
        ]
        pipeline = self._make_pipeline(corpus)
        req = RetrievalRequest(query="original", top_k=5)
        resp = pipeline.retrieve(req)

        assert corpus[0].raw_text == original_raw
        if resp.results:
            assert resp.results[0].candidate.raw_text == original_raw

    def test_cleaned_text_not_modified(self):
        original_cleaned = "Cleaned version that must not change"
        corpus = [
            _make_candidate(
                raw_text="Raw text",
                cleaned_text=original_cleaned,
            ),
        ]
        pipeline = self._make_pipeline(corpus)
        req = RetrievalRequest(query="cleaned", top_k=5)
        resp = pipeline.retrieve(req)

        if resp.results:
            assert resp.results[0].candidate.cleaned_text == original_cleaned

    def test_no_answer_in_response(self):
        corpus = [
            _make_candidate(
                raw_text="Python is a programming language",
                cleaned_text="Python is a programming language",
            ),
        ]
        pipeline = self._make_pipeline(corpus)
        req = RetrievalRequest(query="What is Python?")
        resp = pipeline.retrieve(req)

        d = resp.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "llm" not in d
        assert "generation" not in d
