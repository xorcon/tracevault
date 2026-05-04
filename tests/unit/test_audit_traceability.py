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
    RetrievalScore,
    ScoringCandidate,
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


def _make_scoring(
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
    keyword_score=0.0,
    score_policy="token_frequency",
    matched_fields=None,
    retrieval_source="keyword",
    source_retrievers=None,
) -> ScoringCandidate:
    return ScoringCandidate(
        candidate=CandidateEvidence(
            document_id=document_id,
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            source_path=source_path,
            source_type=source_type,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            raw_text_hash=raw_text_hash,
            cleaned_text_hash=cleaned_text_hash,
            score=RetrievalScore(
                keyword_score=keyword_score,
                score_policy=score_policy,
            ),
            metadata=metadata or {},
        ),
        score=RetrievalScore(
            keyword_score=keyword_score,
            score_policy=score_policy,
        ),
        matched_fields=matched_fields or ["raw_text"],
        retrieval_source=retrieval_source,
        source_retrievers=source_retrievers or ["keyword"],
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
        s = _make_scoring(
            retrieval_source="keyword",
            matched_fields=["raw_text"],
            source_retrievers=["keyword"],
            score_policy="token_frequency",
        )
        trace = build_trace(s, None)
        assert trace.document_id == "doc_001"
        assert trace.chunk_id == "chunk_doc_001_0"
        assert trace.source_path == "docs/test.md"
        assert trace.raw_text_hash == "abc123"
        assert trace.retrieval_source == "keyword"
        assert trace.matched_fields == ["raw_text"]
        assert trace.score_policy == "token_frequency"
        assert trace.source_retrievers == ["keyword"]

    def test_trace_with_filters(self):
        s = _make_scoring(
            retrieval_source="hybrid",
            matched_fields=["raw_text", "cleaned_text"],
            source_retrievers=["keyword", "vector_placeholder"],
            score_policy="hybrid",
        )
        f = MetadataFilter(document_id="doc_001")
        trace = build_trace(s, f)
        assert "document_id=doc_001" in trace.applied_filters

    def test_trace_without_filters(self):
        s = _make_scoring(
            retrieval_source="keyword",
            matched_fields=["raw_text"],
            source_retrievers=["keyword"],
            score_policy="token_frequency",
        )
        trace = build_trace(s, None)
        assert trace.applied_filters == []

    def test_trace_from_scoring_candidate_not_metadata(self):
        """build_trace reads from ScoringCandidate fields, not candidate.metadata."""
        s = _make_scoring(
            retrieval_source="keyword",
            matched_fields=["raw_text"],
            source_retrievers=["keyword"],
            score_policy="token_frequency",
        )
        # candidate.metadata should NOT contain trace fields
        assert "_retrieval_source" not in s.candidate.metadata
        assert "_matched_fields" not in s.candidate.metadata
        # But trace should still be built correctly
        trace = build_trace(s, None)
        assert trace.retrieval_source == "keyword"
        assert trace.matched_fields == ["raw_text"]
        assert trace.source_retrievers == ["keyword"]


class TestRankCandidates:
    def test_rank_is_1_based(self):
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert results[0].rank == 1

    def test_top_k_limits(self):
        corpus = [
            _make_scoring(chunk_id=f"chunk_doc_001_{i}", chunk_index=i)
            for i in range(10)
        ]
        results = rank_candidates(corpus, "run_001", "qhash", 3, None)
        assert len(results) == 3

    def test_run_id_and_query_hash(self):
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert results[0].retrieval_run_id == "run_001"
        assert results[0].query_hash == "qhash"

    def test_result_has_trace(self):
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert hasattr(results[0], "trace")
        assert results[0].trace.document_id == "doc_001"

    def test_candidate_metadata_not_polluted(self):
        """rank_candidates must not write trace fields into candidate.metadata."""
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        c = results[0].candidate
        assert "_matched_fields" not in c.metadata
        assert "_retrieval_source" not in c.metadata
        assert "_source_retrievers" not in c.metadata


class TestBuildResponse:
    def test_response_fields(self):
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        resp = build_response(
            results=results,
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
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        f = MetadataFilter(document_id="doc_001")
        resp = build_response(
            results=results,
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

        # Trace is on RetrievalResult, not CandidateEvidence
        t = r.trace
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
            # Trace is in result serialization
            assert "trace" in r
            assert r["trace"]["document_id"] == "doc_001"

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


class TestTraceOnResultNotCandidate:
    """Verify trace is on RetrievalResult, not CandidateEvidence."""

    def test_candidate_has_no_trace(self):
        c = _make_candidate()
        assert not hasattr(c, "trace")

    def test_result_has_trace(self):
        s = _make_scoring()
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert hasattr(results[0], "trace")

    def test_trace_has_score_policy(self):
        s = _make_scoring(score_policy="token_frequency")
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert results[0].trace.score_policy == "token_frequency"

    def test_trace_has_source_retrievers(self):
        s = _make_scoring(source_retrievers=["keyword"])
        results = rank_candidates([s], "run_001", "qhash", 5, None)
        assert results[0].trace.source_retrievers == ["keyword"]

    def test_trace_has_applied_filters(self):
        s = _make_scoring()
        f = MetadataFilter(document_id="doc_001")
        results = rank_candidates([s], "run_001", "qhash", 5, f)
        assert "document_id=doc_001" in results[0].trace.applied_filters

    def test_same_candidate_two_runs_no_stale_trace(self):
        """Same CandidateEvidence used in two runs — traces are independent."""
        s = _make_scoring()

        results1 = rank_candidates([s], "run_001", "qhash1", 5, None)
        results2 = rank_candidates([s], "run_002", "qhash2", 5, None)

        assert results1[0].retrieval_run_id == "run_001"
        assert results2[0].retrieval_run_id == "run_002"
        assert results1[0].query_hash == "qhash1"
        assert results2[0].query_hash == "qhash2"

        # Candidate is unchanged
        assert s.candidate.raw_text == "Hello world"
        # candidate.metadata is clean
        assert "_matched_fields" not in s.candidate.metadata
        assert "_retrieval_source" not in s.candidate.metadata


class TestNoStaleTraceAcrossRuns:
    """No stale trace metadata survives across retrieval runs."""

    def _make_pipeline(self, corpus):
        kw = InMemoryKeywordRetriever(corpus)
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        return HybridRetrievalPipeline(kw, vec)

    def test_two_pipeline_runs_no_stale(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = self._make_pipeline(corpus)

        resp1 = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_001"))
        resp2 = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_002"))

        # Traces are independent
        assert resp1.results[0].retrieval_run_id == "run_001"
        assert resp2.results[0].retrieval_run_id == "run_002"

        # Corpus is clean
        for key in ["_matched_fields", "_retrieval_source", "_source_retrievers"]:
            assert key not in corpus[0].metadata

        # Result candidates are clean
        for key in ["_matched_fields", "_retrieval_source", "_source_retrievers"]:
            assert key not in resp1.results[0].candidate.metadata
            assert key not in resp2.results[0].candidate.metadata

    def test_corpus_metadata_clean_after_retrieval(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = self._make_pipeline(corpus)
        pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))

        for key in ["_matched_fields", "_retrieval_source", "_source_retrievers"]:
            assert key not in corpus[0].metadata, f"{key} leaked into corpus metadata"


class TestScoringCandidateTraceFields:
    """ScoringCandidate carries trace fields, not candidate.metadata."""

    def test_scoring_candidate_has_trace_fields(self):
        s = _make_scoring(
            retrieval_source="keyword",
            matched_fields=["raw_text"],
            source_retrievers=["keyword"],
        )
        assert s.retrieval_source == "keyword"
        assert s.matched_fields == ["raw_text"]
        assert s.source_retrievers == ["keyword"]
        # Not in candidate.metadata
        assert "_retrieval_source" not in s.candidate.metadata
        assert "_matched_fields" not in s.candidate.metadata
        assert "_source_retrievers" not in s.candidate.metadata

    def test_build_trace_reads_from_scoring_candidate(self):
        s = _make_scoring(
            retrieval_source="hybrid",
            matched_fields=["cleaned_text", "raw_text"],
            source_retrievers=["keyword", "vector_placeholder"],
            score_policy="hybrid",
        )
        trace = build_trace(s, None)
        assert trace.retrieval_source == "hybrid"
        assert trace.matched_fields == ["cleaned_text", "raw_text"]
        assert trace.source_retrievers == ["keyword", "vector_placeholder"]
        assert trace.score_policy == "hybrid"


class TestPipelineTextPolicyOverrideFailsOnOldBehavior:
    """This test would fail on the previous behavior where request.text_policy was not enforced."""

    def test_request_policy_overrides_retriever_default_in_pipeline(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        # Pipeline built with RAW_ONLY
        kw = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        pipeline = HybridRetrievalPipeline(kw, vec)

        # Request with CLEANED_ONLY — should find "cleanedword"
        # On old behavior, this would fail because keyword retriever would use RAW_ONLY
        req = RetrievalRequest(
            query="cleanedword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1, (
            "request.text_policy=CLEANED_ONLY should find 'cleanedword' in cleaned_text, "
            "but pipeline did not enforce request policy"
        )
        assert resp.text_policy.mode == "CLEANED_ONLY"


class TestRetrievalResultTraceFromPipeline:
    """Pipeline-level: trace fields come from ScoringCandidate, not candidate.metadata."""

    def test_trace_has_retrieval_source(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.trace.retrieval_source in ("keyword", "hybrid")

    def test_trace_has_matched_fields(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.matched_fields) >= 1

    def test_trace_has_source_retrievers(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.source_retrievers) >= 1

    def test_candidate_metadata_clean_after_pipeline(self):
        """Pipeline results should have clean candidate.metadata."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        c = resp.results[0].candidate
        assert "_matched_fields" not in c.metadata
        assert "_retrieval_source" not in c.metadata
        assert "_source_retrievers" not in c.metadata

    def test_response_text_policy_equals_executed_policy(self):
        """Response.text_policy must equal the actual executed policy."""
        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        kw = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        pipeline = HybridRetrievalPipeline(kw, vec)

        # Request with CLEANED_ONLY
        req = RetrievalRequest(
            query="cleanedword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "CLEANED_ONLY"
        assert len(resp.results) == 1

        # Request with RAW_ONLY
        req_raw = RetrievalRequest(
            query="rawword", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        resp_raw = pipeline.retrieve(req_raw)
        assert resp_raw.text_policy.mode == "RAW_ONLY"
        assert len(resp_raw.results) == 1

    def test_pipeline_text_policy_override_affects_search(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        # Pipeline built with RAW_ONLY
        kw = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        pipeline = HybridRetrievalPipeline(kw, vec)

        # Request with CLEANED_ONLY should find "cleanedword"
        req_clean = RetrievalRequest(
            query="cleanedword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp_clean = pipeline.retrieve(req_clean)
        assert len(resp_clean.results) == 1
        assert resp_clean.text_policy.mode == "CLEANED_ONLY"

        # Request with CLEANED_ONLY — keyword retriever should NOT find "rawword"
        # (vector placeholder always returns, but keyword source should be absent)
        resp_no_match = pipeline.retrieve(
            RetrievalRequest(query="rawword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only())
        )
        # Any result should come from vector_placeholder, not keyword
        for r in resp_no_match.results:
            assert "keyword" not in r.trace.source_retrievers

    def test_pipeline_raw_only_finds_raw_term(self):
        """RAW_ONLY request finds a term only in raw_text."""
        corpus = [
            _make_candidate(raw_text="SECRET keyword", cleaned_text="cleaned text"),
        ]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(
            query="SECRET", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_pipeline_cleaned_only_finds_cleaned_term(self):
        """CLEANED_ONLY request finds a term only in cleaned_text."""
        corpus = [
            _make_candidate(raw_text="raw text", cleaned_text="CLEANED keyword"),
        ]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(
            query="CLEANED", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_pipeline_cleaned_only_preserves_raw_text(self):
        """CLEANED_ONLY response still preserves raw_text."""
        corpus = [
            _make_candidate(raw_text="Original raw content", cleaned_text="CLEANED keyword"),
        ]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        req = RetrievalRequest(
            query="CLEANED", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1
        assert resp.results[0].candidate.raw_text == "Original raw content"


class TestTwoRunsSameCandidateNoStaleTrace:
    """Same CandidateEvidence reused across two retrieval runs — no stale trace."""

    def test_two_different_requests_different_traces(self):
        """Two different RetrievalRequests against same corpus produce different traces."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )

        req1 = RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_001")
        resp1 = pipeline.retrieve(req1)

        req2 = RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_002")
        resp2 = pipeline.retrieve(req2)

        # Different run IDs
        assert resp1.results[0].retrieval_run_id == "run_001"
        assert resp2.results[0].retrieval_run_id == "run_002"

        # Corpus candidate.metadata is clean
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata
        assert "_source_retrievers" not in corpus[0].metadata

    def test_original_corpus_metadata_clean_after_retrieval(self):
        """Original corpus candidate.metadata does not contain run-specific keys."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))

        run_specific_keys = ["_matched_fields", "_retrieval_source", "_source_retrievers"]
        for key in run_specific_keys:
            assert key not in corpus[0].metadata, f"{key} leaked into corpus metadata"

    def test_per_result_trace_contains_required_fields(self):
        """Per-result trace contains retrieval_source, matched_fields, etc."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        resp = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))
        t = resp.results[0].trace
        assert t.retrieval_source != ""
        assert len(t.matched_fields) >= 1
        assert len(t.source_retrievers) >= 1
        assert t.score_policy != ""

    def test_serialization_preserves_per_result_trace(self):
        """Serialization preserves per-result trace metadata."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )
        resp = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))
        d = resp.to_dict()
        r = d["results"][0]
        assert "trace" in r
        assert r["trace"]["retrieval_source"] != ""
        assert len(r["trace"]["matched_fields"]) >= 1
        assert len(r["trace"]["source_retrievers"]) >= 1
        assert r["trace"]["score_policy"] != ""

    def test_no_stale_trace_metadata_survives_across_runs(self):
        """No stale trace metadata survives across runs."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = HybridRetrievalPipeline(
            InMemoryKeywordRetriever(corpus),
            InMemoryVectorRetrieverPlaceholder(corpus),
        )

        resp1 = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_001"))
        resp2 = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_002"))

        # Traces are independent
        assert resp1.results[0].retrieval_run_id == "run_001"
        assert resp2.results[0].retrieval_run_id == "run_002"

        # Corpus is clean
        for key in ["_matched_fields", "_retrieval_source", "_source_retrievers"]:
            assert key not in corpus[0].metadata

        # Result candidates are clean
        for key in ["_matched_fields", "_retrieval_source", "_source_retrievers"]:
            assert key not in resp1.results[0].candidate.metadata
            assert key not in resp2.results[0].candidate.metadata


class TestScoringCandidateIsolation:
    """ScoringCandidate trace fields are independent per run."""

    def test_same_candidate_two_scoring_candidates(self):
        """Same corpus candidate produces two independent ScoringCandidate instances."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)

        s1 = retriever.retrieve("Python", top_k=5)[0]
        s2 = retriever.retrieve("Python", top_k=5)[0]

        # Same corpus candidate
        assert s1.candidate is corpus[0]
        assert s2.candidate is corpus[0]

        # Independent ScoringCandidate instances
        assert s1 is not s2

    def test_scoring_candidate_trace_fields_not_in_candidate_metadata(self):
        """ScoringCandidate trace fields are not in candidate.metadata."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)
        s = retriever.retrieve("Python", top_k=5)[0]

        assert s.retrieval_source == "keyword"
        assert "_retrieval_source" not in s.candidate.metadata
        assert "_matched_fields" not in s.candidate.metadata
        assert "_source_retrievers" not in s.candidate.metadata


