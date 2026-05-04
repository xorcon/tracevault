"""Tests for in-memory vector retriever placeholder."""

from tracevault.retrieval.models import CandidateEvidence, ScoringCandidate
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
        metadata=metadata or {},
    )


class TestDeterministicScore:
    def test_same_input_same_output(self):
        from tracevault.retrieval.vector import _deterministic_score
        s1 = _deterministic_score("query", "chunk_001")
        s2 = _deterministic_score("query", "chunk_001")
        assert s1 == s2

    def test_different_chunk_different_score(self):
        from tracevault.retrieval.vector import _deterministic_score
        s1 = _deterministic_score("query", "chunk_001")
        s2 = _deterministic_score("query", "chunk_002")
        assert s1 != s2

    def test_different_query_different_score(self):
        from tracevault.retrieval.vector import _deterministic_score
        s1 = _deterministic_score("query1", "chunk_001")
        s2 = _deterministic_score("query2", "chunk_001")
        assert s1 != s2

    def test_score_in_range(self):
        from tracevault.retrieval.vector import _deterministic_score
        s = _deterministic_score("query", "chunk_001")
        assert 0.0 <= s <= 1.0


class TestInMemoryVectorRetrieverPlaceholder:
    def test_basic_retrieval(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming language",
                cleaned_text="Python programming language",
            ),
        ]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert isinstance(results[0], ScoringCandidate)
        assert results[0].score.vector_score > 0

    def test_empty_query_returns_empty(self):
        retriever = InMemoryVectorRetrieverPlaceholder([])
        results = retriever.retrieve("")
        assert len(results) == 0

    def test_whitespace_query_returns_empty(self):
        retriever = InMemoryVectorRetrieverPlaceholder([])
        results = retriever.retrieve("   ")
        assert len(results) == 0

    def test_top_k_limits_results(self):
        corpus = [
            _make_candidate(
                chunk_id=f"chunk_doc_001_{i}",
                chunk_index=i,
                raw_text="Python programming",
                cleaned_text="Python programming",
            )
            for i in range(10)
        ]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=3)
        assert len(results) == 3

    def test_scores_are_deterministic(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results1 = retriever.retrieve("Python", top_k=5)
        results2 = retriever.retrieve("Python", top_k=5)
        assert results1[0].score.vector_score == results2[0].score.vector_score

    def test_retrieval_source_is_vector_placeholder(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        retriever.retrieve("Python", top_k=5)
        assert retriever.source_type == "vector_placeholder"

    def test_score_in_range(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert 0.0 <= s.score.vector_score <= 1.0

    def test_keyword_score_is_zero(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert s.score.keyword_score == 0.0

    def test_score_policy_is_deterministic_placeholder(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert s.score.score_policy == "deterministic_placeholder"

    def test_no_bm25_in_score_policy(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert "bm25" not in s.score.score_policy.lower()

    def test_filter_by_document_id(self):
        corpus = [
            _make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python"),
            _make_candidate(document_id="doc_002", raw_text="Python", cleaned_text="Python"),
        ]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", filters={"document_id": "doc_001"}, top_k=5)
        for s in results:
            assert s.candidate.document_id == "doc_001"

    def test_filter_no_match_returns_empty(self):
        corpus = [_make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", filters={"document_id": "doc_999"}, top_k=5)
        assert len(results) == 0

    def test_does_not_modify_corpus(self):
        corpus = [_make_candidate(raw_text="Original", cleaned_text="Original")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        retriever.retrieve("Original", top_k=5)
        assert corpus[0].raw_text == "Original"
        assert corpus[0].cleaned_text == "Original"

    def test_source_type_is_vector_placeholder(self):
        retriever = InMemoryVectorRetrieverPlaceholder([])
        assert retriever.source_type == "vector_placeholder"

    def test_no_external_call(self):
        """Placeholder must not make any external calls."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        # Should not hang or raise — no network, no embedding, no LLM
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1

    def test_sorted_by_vector_score_desc(self):
        corpus = [
            _make_candidate(chunk_id="chunk_doc_001_0", raw_text="Python", cleaned_text="Python"),
            _make_candidate(chunk_id="chunk_doc_001_1", raw_text="Python", cleaned_text="Python"),
        ]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 2
        assert results[0].score.vector_score >= results[1].score.vector_score

    def test_matched_fields_empty(self):
        """Vector placeholder does not inspect text, so matched_fields is empty."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert results[0].matched_fields == []

    def test_does_not_claim_cleaned_text_match(self):
        """Vector placeholder must not claim cleaned_text was matched."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        fields = results[0].matched_fields
        assert "cleaned_text" not in fields

    def test_scoring_candidate_has_trace_fields(self):
        """Vector placeholder ScoringCandidate has trace fields."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        s = results[0]
        assert s.retrieval_source == "vector_placeholder"
        assert s.source_retrievers == ["vector_placeholder"]
        assert s.matched_fields == []

    def test_candidate_metadata_not_polluted(self):
        """Vector placeholder must not write run-specific keys into candidate.metadata."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert "_matched_fields" not in results[0].candidate.metadata
        assert "_retrieval_source" not in results[0].candidate.metadata
        assert "_source_retrievers" not in results[0].candidate.metadata

    def test_corpus_candidate_metadata_clean(self):
        """Corpus CandidateEvidence.metadata must not be mutated by retrieval."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        retriever.retrieve("Python", top_k=5)
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata
        assert "_source_retrievers" not in corpus[0].metadata


class TestScoringCandidateFromVectorRetriever:
    """Vector placeholder returns ScoringCandidate with trace fields."""

    def test_result_is_scoring_candidate(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert isinstance(results[0], ScoringCandidate)

    def test_scoring_candidate_candidate_is_corpus_reference(self):
        """ScoringCandidate.candidate is the corpus CandidateEvidence."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert results[0].candidate is corpus[0]


class TestNoStaleMetadataAcrossRuns:
    """Same corpus candidate reused across two retrieval runs."""

    def test_two_runs_no_stale_metadata(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)

        results1 = retriever.retrieve("Python", top_k=5)
        results2 = retriever.retrieve("Python", top_k=5)

        # Corpus candidate.metadata is clean
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata

        # ScoringCandidate trace fields are independent
        assert results1[0].retrieval_source == "vector_placeholder"
        assert results2[0].retrieval_source == "vector_placeholder"


class TestVectorRetrieverTextPolicyParameter:
    """Vector placeholder accepts text_policy parameter for protocol compatibility."""

    def test_accepts_text_policy_parameter(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        # Should not raise — text_policy is accepted but unused
        results = retriever.retrieve(
            "Python", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        assert len(results) == 1


class TestRetrievalResultTraceFromPipeline:
    """Pipeline-level: trace fields come from ScoringCandidate, not candidate.metadata."""

    def test_trace_has_retrieval_source(self):
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.trace.retrieval_source in ("keyword", "hybrid")

    def test_trace_has_matched_fields(self):
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.matched_fields) >= 1

    def test_trace_has_source_retrievers(self):
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.source_retrievers) >= 1

    def test_candidate_metadata_clean_after_pipeline(self):
        """Pipeline results should have clean candidate.metadata."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        c = resp.results[0].candidate
        assert "_matched_fields" not in c.metadata
        assert "_retrieval_source" not in c.metadata
        assert "_source_retrievers" not in c.metadata

    def test_response_text_policy_equals_executed_policy(self):
        """Response.text_policy must equal the actual executed policy."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())

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
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        # Pipeline built with RAW_ONLY
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())

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
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="SECRET keyword", cleaned_text="cleaned text"),
        ]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(
            query="SECRET", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_pipeline_cleaned_only_finds_cleaned_term(self):
        """CLEANED_ONLY request finds a term only in cleaned_text."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="raw text", cleaned_text="CLEANED keyword"),
        ]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(
            query="CLEANED", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_pipeline_cleaned_only_preserves_raw_text(self):
        """CLEANED_ONLY response still preserves raw_text."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="Original raw content", cleaned_text="CLEANED keyword"),
        ]
        pipeline = create_pipeline(corpus)
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
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = create_pipeline(corpus)

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
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))

        run_specific_keys = ["_matched_fields", "_retrieval_source", "_source_retrievers"]
        for key in run_specific_keys:
            assert key not in corpus[0].metadata, f"{key} leaked into corpus metadata"

    def test_per_result_trace_contains_required_fields(self):
        """Per-result trace contains retrieval_source, matched_fields, etc."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        resp = pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))
        t = resp.results[0].trace
        assert t.retrieval_source != ""
        assert len(t.matched_fields) >= 1
        assert len(t.source_retrievers) >= 1
        assert t.score_policy != ""

    def test_serialization_preserves_per_result_trace(self):
        """Serialization preserves per-result trace metadata."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
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
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)

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
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)

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
        retriever = InMemoryVectorRetrieverPlaceholder(corpus)
        s = retriever.retrieve("Python", top_k=5)[0]

        assert s.retrieval_source == "vector_placeholder"
        assert "_retrieval_source" not in s.candidate.metadata
        assert "_matched_fields" not in s.candidate.metadata
        assert "_source_retrievers" not in s.candidate.metadata


class TestPipelineTextPolicyOverrideFailsOnOldBehavior:
    """This test would fail on the previous behavior where request.text_policy was not enforced."""

    def test_request_policy_overrides_retriever_default_in_pipeline(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy

        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        # Pipeline built with RAW_ONLY
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())

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
