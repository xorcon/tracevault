"""Tests for in-memory keyword retriever."""

from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import CandidateEvidence, ScoringCandidate, TextRetrievalPolicy


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


class TestInMemoryKeywordRetriever:
    def test_basic_retrieval(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming language",
                cleaned_text="Python programming language",
            ),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert isinstance(results[0], ScoringCandidate)
        assert results[0].score.keyword_score > 0

    def test_empty_query_returns_empty(self):
        retriever = InMemoryKeywordRetriever([])
        results = retriever.retrieve("")
        assert len(results) == 0

    def test_whitespace_query_returns_empty(self):
        retriever = InMemoryKeywordRetriever([])
        results = retriever.retrieve("   ")
        assert len(results) == 0

    def test_no_match_returns_empty(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Java")
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
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=3)
        assert len(results) == 3

    def test_scores_are_positive(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert s.score.keyword_score > 0

    def test_scores_in_range(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert 0.0 <= s.score.keyword_score <= 1.0

    def test_sorted_by_keyword_score_desc(self):
        corpus = [
            _make_candidate(chunk_id="chunk_doc_001_0", raw_text="Python Python Python", cleaned_text="Python Python Python"),
            _make_candidate(chunk_id="chunk_doc_001_1", raw_text="Python", cleaned_text="Python"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 2
        assert results[0].score.keyword_score >= results[1].score.keyword_score

    def test_vector_score_is_zero(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert s.score.vector_score == 0.0

    def test_source_type_is_keyword(self):
        retriever = InMemoryKeywordRetriever([])
        assert retriever.source_type == "keyword"

    def test_score_policy_is_token_frequency(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert s.score.score_policy == "token_frequency"

    def test_no_bm25_in_score_policy(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        for s in results:
            assert "bm25" not in s.score.score_policy.lower()

    def test_filter_by_document_id(self):
        corpus = [
            _make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python"),
            _make_candidate(document_id="doc_002", raw_text="Python", cleaned_text="Python"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", filters={"document_id": "doc_001"}, top_k=5)
        for s in results:
            assert s.candidate.document_id == "doc_001"

    def test_filter_no_match_returns_empty(self):
        corpus = [_make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", filters={"document_id": "doc_999"}, top_k=5)
        assert len(results) == 0

    def test_filter_by_key_value(self):
        corpus = [
            _make_candidate(metadata={"env": "prod"}, raw_text="Python", cleaned_text="Python"),
            _make_candidate(metadata={"env": "dev"}, raw_text="Python", cleaned_text="Python"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", filters={"env": "prod"}, top_k=5)
        for s in results:
            assert s.candidate.metadata["env"] == "prod"

    def test_does_not_modify_corpus(self):
        corpus = [_make_candidate(raw_text="Original", cleaned_text="Original")]
        retriever = InMemoryKeywordRetriever(corpus)
        retriever.retrieve("Original", top_k=5)
        assert corpus[0].raw_text == "Original"
        assert corpus[0].cleaned_text == "Original"

    def test_matched_fields_raw_only(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert "raw_text" in results[0].matched_fields

    def test_matched_fields_cleaned_only(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert "cleaned_text" in results[0].matched_fields

    def test_matched_fields_dual_context(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.dual_context())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        fields = results[0].matched_fields
        assert "raw_text" in fields
        assert "cleaned_text" in fields

    def test_raw_only_searches_raw_text(self):
        corpus = [
            _make_candidate(raw_text="Python programming", cleaned_text="Java programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1

    def test_cleaned_only_searches_cleaned_text(self):
        corpus = [
            _make_candidate(raw_text="Java programming", cleaned_text="Python programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1

    def test_raw_only_does_not_blank_raw_text(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        results = retriever.retrieve("Python", top_k=5)
        assert results[0].candidate.raw_text == "Python programming"
        assert results[0].candidate.cleaned_text == "Python programming"

    def test_cleaned_only_does_not_blank_raw_text(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        results = retriever.retrieve("Python", top_k=5)
        assert results[0].candidate.raw_text == "Python programming"
        assert results[0].candidate.cleaned_text == "Python programming"

    def test_candidate_metadata_not_polluted(self):
        """ScoringCandidate must not write _matched_fields into candidate.metadata."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        # candidate.metadata should NOT contain run-specific keys
        assert "_matched_fields" not in results[0].candidate.metadata
        assert "_retrieval_source" not in results[0].candidate.metadata
        assert "_source_retrievers" not in results[0].candidate.metadata
        # Trace fields live on ScoringCandidate
        assert "raw_text" in results[0].matched_fields
        assert results[0].retrieval_source == "keyword"
        assert results[0].source_retrievers == ["keyword"]

    def test_corpus_candidate_metadata_clean(self):
        """Corpus CandidateEvidence.metadata must not be mutated by retrieval."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)
        retriever.retrieve("Python", top_k=5)
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata
        assert "_source_retrievers" not in corpus[0].metadata


class TestKeywordRetrieverTextPolicyOverride:
    """Per-request text_policy overrides constructor default."""

    def test_request_policy_overrides_constructor_default(self):
        """Retriever built with RAW_ONLY, request uses CLEANED_ONLY."""
        corpus = [
            _make_candidate(raw_text="Java programming", cleaned_text="Python programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        # Request overrides to CLEANED_ONLY
        results = retriever.retrieve(
            "Python", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        assert len(results) == 1
        assert "cleaned_text" in results[0].matched_fields

    def test_request_policy_raw_only(self):
        """Retriever built with DUAL_CONTEXT, request uses RAW_ONLY."""
        corpus = [
            _make_candidate(raw_text="Python programming", cleaned_text="Java programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.dual_context())
        results = retriever.retrieve(
            "Python", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        assert len(results) == 1
        assert "raw_text" in results[0].matched_fields
        assert "cleaned_text" not in results[0].matched_fields

    def test_no_request_policy_uses_constructor_default(self):
        """When request text_policy is None, constructor default is used."""
        corpus = [
            _make_candidate(raw_text="Python programming", cleaned_text="Java programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert "raw_text" in results[0].matched_fields

    def test_cleaned_only_preserves_raw_text_in_candidate(self):
        """CLEANED_ONLY searches cleaned_text but preserves raw_text in candidate."""
        corpus = [
            _make_candidate(raw_text="Original raw", cleaned_text="Python programming"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        results = retriever.retrieve("Python", top_k=5)
        assert len(results) == 1
        assert results[0].candidate.raw_text == "Original raw"
        assert results[0].candidate.cleaned_text == "Python programming"

    def test_raw_only_finds_term_only_in_raw_text(self):
        """RAW_ONLY finds a term that only exists in raw_text."""
        corpus = [
            _make_candidate(raw_text="SECRET keyword", cleaned_text="cleaned text"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        results = retriever.retrieve("SECRET", top_k=5)
        assert len(results) == 1

    def test_cleaned_only_misses_term_only_in_raw_text(self):
        """CLEANED_ONLY does not find a term that only exists in raw_text."""
        corpus = [
            _make_candidate(raw_text="SECRET keyword", cleaned_text="cleaned text"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        results = retriever.retrieve("SECRET", top_k=5)
        assert len(results) == 0

    def test_raw_only_finds_term_only_in_raw_not_cleaned(self):
        """RAW_ONLY request finds a term only in raw_text."""
        corpus = [
            _make_candidate(raw_text="rawterm here", cleaned_text="cleanedterm here"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("rawterm", top_k=5, text_policy=TextRetrievalPolicy.raw_only())
        assert len(results) == 1

    def test_cleaned_only_finds_term_only_in_cleaned(self):
        """CLEANED_ONLY request finds a term only in cleaned_text."""
        corpus = [
            _make_candidate(raw_text="rawterm here", cleaned_text="cleanedterm here"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("cleanedterm", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only())
        assert len(results) == 1

    def test_cleaned_only_response_preserves_raw_text(self):
        """CLEANED_ONLY response still preserves raw_text in candidate."""
        corpus = [
            _make_candidate(raw_text="raw content preserved", cleaned_text="cleanedterm here"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("cleanedterm", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only())
        assert len(results) == 1
        assert results[0].candidate.raw_text == "raw content preserved"

    def test_request_policy_controls_actual_search_behavior(self):
        """Build retriever with one default policy, send request with different policy."""
        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        retriever = InMemoryKeywordRetriever(corpus, text_policy=TextRetrievalPolicy.raw_only())
        # Request uses CLEANED_ONLY — should find "cleanedword", not "rawword"
        results = retriever.retrieve(
            "cleanedword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        assert len(results) == 1
        # Same retriever, RAW_ONLY — should find "rawword", not "cleanedword"
        results_raw = retriever.retrieve(
            "rawword", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        assert len(results_raw) == 1
        # CLEANED_ONLY should NOT find "rawword"
        results_clean = retriever.retrieve(
            "rawword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        assert len(results_clean) == 0


class TestScoringCandidateFromRetriever:
    """Keyword retriever returns ScoringCandidate with trace fields."""

    def test_result_is_scoring_candidate(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert isinstance(results[0], ScoringCandidate)

    def test_scoring_candidate_has_trace_fields(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        s = results[0]
        assert s.retrieval_source == "keyword"
        assert s.source_retrievers == ["keyword"]
        assert len(s.matched_fields) >= 1

    def test_scoring_candidate_candidate_is_corpus_reference(self):
        """ScoringCandidate.candidate is the corpus CandidateEvidence."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        retriever = InMemoryKeywordRetriever(corpus)
        results = retriever.retrieve("Python", top_k=5)
        assert results[0].candidate is corpus[0]


class TestNoStaleMetadataAcrossRuns:
    """Same corpus candidate reused across two retrieval runs."""

    def test_two_runs_no_stale_metadata(self):
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        retriever = InMemoryKeywordRetriever(corpus)

        results1 = retriever.retrieve("Python", top_k=5)
        results2 = retriever.retrieve("Python", top_k=5)

        # Corpus candidate.metadata is clean
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata

        # ScoringCandidate trace fields are independent
        assert results1[0].retrieval_source == "keyword"
        assert results2[0].retrieval_source == "keyword"

    def test_two_different_queries_no_stale(self):
        corpus = [
            _make_candidate(chunk_id="chunk_001", raw_text="Python programming", cleaned_text="Python programming"),
            _make_candidate(chunk_id="chunk_002", raw_text="Java development", cleaned_text="Java development"),
        ]
        retriever = InMemoryKeywordRetriever(corpus)

        results1 = retriever.retrieve("Python", top_k=5)
        results2 = retriever.retrieve("Java", top_k=5)

        # Different queries, different results
        assert results1[0].candidate.chunk_id == "chunk_001"
        assert results2[0].candidate.chunk_id == "chunk_002"

        # Corpus clean
        for c in corpus:
            assert "_matched_fields" not in c.metadata
            assert "_retrieval_source" not in c.metadata


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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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


class TestPipelineTextPolicyOverrideFailsOnOldBehavior:
    """This test would fail on the previous behavior where request.text_policy was not enforced."""

    def test_request_policy_overrides_retriever_default_in_pipeline(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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
        from tracevault.retrieval.models import RetrievalRequest

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


class TestPipelineTextPolicyOverrideFailsOnOldBehavior:
    """This test would fail on the previous behavior where request.text_policy was not enforced."""

    def test_request_policy_overrides_retriever_default_in_pipeline(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        from tracevault.retrieval.pipeline import create_pipeline
        from tracevault.retrieval.models import RetrievalRequest

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
