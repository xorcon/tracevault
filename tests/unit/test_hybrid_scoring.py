"""Tests for hybrid scoring and merge."""

import pytest

from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import CandidateEvidence, RetrievalScore, ScoringCandidate
from tracevault.retrieval.scoring import HybridScoreMerger


def _make_scoring(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
    keyword_score=0.0,
    vector_score=0.0,
    score_policy="token_frequency",
    matched_fields=None,
    retrieval_source="keyword",
    source_retrievers=None,
) -> ScoringCandidate:
    return ScoringCandidate(
        candidate=CandidateEvidence(
            document_id=document_id,
            chunk_id=chunk_id,
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello world",
            cleaned_text="Hello world",
            raw_text_hash="abc123",
            metadata={},
        ),
        score=RetrievalScore(
            keyword_score=keyword_score,
            vector_score=vector_score,
            hybrid_score=0.0,
            score_policy=score_policy,
        ),
        matched_fields=matched_fields or ["raw_text"],
        retrieval_source=retrieval_source,
        source_retrievers=source_retrievers or ["keyword"],
    )


class TestHybridScoreMerger:
    def test_alpha_validation_rejects_negative(self):
        with pytest.raises(ValueError, match="alpha"):
            HybridScoreMerger(alpha=-0.1)

    def test_alpha_validation_rejects_over_one(self):
        with pytest.raises(ValueError, match="alpha"):
            HybridScoreMerger(alpha=1.1)

    def test_alpha_boundary_zero(self):
        merger = HybridScoreMerger(alpha=0.0)
        assert merger.alpha == 0.0

    def test_alpha_boundary_one(self):
        merger = HybridScoreMerger(alpha=1.0)
        assert merger.alpha == 1.0

    def test_alpha_zero_keyword_only(self):
        merger = HybridScoreMerger(alpha=0.0)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert len(merged) == 1
        assert merged[0].score.hybrid_score == 0.8
        assert merged[0].score.keyword_score == 0.8
        assert merged[0].score.vector_score == 0.6

    def test_alpha_one_vector_only(self):
        merger = HybridScoreMerger(alpha=1.0)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert len(merged) == 1
        assert merged[0].score.hybrid_score == 0.6

    def test_alpha_half_merge(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert len(merged) == 1
        assert merged[0].score.hybrid_score == 0.7

    def test_deduplication(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert len(merged) == 1

    def test_keyword_only_results(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        merged = merger.merge(kw, [])
        assert len(merged) == 1
        assert merged[0].score.keyword_score == 0.8
        assert merged[0].score.vector_score == 0.0
        assert merged[0].retrieval_source == "keyword"

    def test_vector_only_results(self):
        merger = HybridScoreMerger(alpha=0.5)
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge([], vec)
        assert len(merged) == 1
        assert merged[0].score.keyword_score == 0.0
        assert merged[0].score.vector_score == 0.6
        assert merged[0].retrieval_source == "vector_placeholder"

    def test_hybrid_source_when_both(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert merged[0].retrieval_source == "hybrid"

    def test_empty_results(self):
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([], [])
        assert len(merged) == 0

    def test_deterministic_tie_break(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [
            _make_scoring(document_id="doc_002", chunk_id="chunk_002", keyword_score=0.5),
            _make_scoring(document_id="doc_001", chunk_id="chunk_001", keyword_score=0.5),
        ]
        merged = merger.merge(kw, [])
        assert merged[0].candidate.document_id == "doc_001"
        assert merged[1].candidate.document_id == "doc_002"

    def test_ranking_by_hybrid_score_desc(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [
            _make_scoring(chunk_id="chunk_001", keyword_score=0.9),
            _make_scoring(chunk_id="chunk_002", keyword_score=0.3),
        ]
        merged = merger.merge(kw, [])
        assert merged[0].candidate.chunk_id == "chunk_001"
        assert merged[1].candidate.chunk_id == "chunk_002"

    def test_tie_break_keyword_score(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [
            _make_scoring(chunk_id="chunk_001", keyword_score=0.8),
            _make_scoring(chunk_id="chunk_002", keyword_score=0.6),
        ]
        vec = [
            _make_scoring(chunk_id="chunk_001", vector_score=0.4, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"]),
            _make_scoring(chunk_id="chunk_002", vector_score=0.8, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"]),
        ]
        merged = merger.merge(kw, vec)
        assert merged[0].candidate.chunk_id == "chunk_002"
        assert merged[1].candidate.chunk_id == "chunk_001"

    def test_alpha_stored_in_score(self):
        merger = HybridScoreMerger(alpha=0.7)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.5)]
        merged = merger.merge(kw, [])
        assert merged[0].score.alpha == 0.7

    def test_preserves_raw_text(self):
        s = _make_scoring(chunk_id="chunk_001", keyword_score=0.5)
        s.candidate.raw_text = "Original raw text"
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([s], [])
        assert merged[0].candidate.raw_text == "Original raw text"

    def test_score_policy_token_frequency_keyword_only(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        merged = merger.merge(kw, [])
        assert merged[0].score.score_policy == "token_frequency"

    def test_score_policy_deterministic_placeholder_vector_only(self):
        merger = HybridScoreMerger(alpha=0.5)
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge([], vec)
        assert merged[0].score.score_policy == "deterministic_placeholder"

    def test_score_policy_hybrid_when_both(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert merged[0].score.score_policy == "hybrid"

    def test_matched_fields_sorted_deterministic(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8, matched_fields=["cleaned_text", "raw_text"])]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"], matched_fields=[])]
        merged = merger.merge(kw, vec)
        assert merged[0].matched_fields == ["cleaned_text", "raw_text"]

    def test_source_retrievers_keyword_only(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        merged = merger.merge(kw, [])
        assert merged[0].source_retrievers == ["keyword"]

    def test_source_retrievers_vector_only(self):
        merger = HybridScoreMerger(alpha=0.5)
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge([], vec)
        assert merged[0].source_retrievers == ["vector_placeholder"]

    def test_source_retrievers_hybrid(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        assert merged[0].source_retrievers == ["keyword", "vector_placeholder"]

    def test_candidate_metadata_not_polluted(self):
        """Merger must not write run-specific keys into candidate.metadata."""
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]
        merged = merger.merge(kw, vec)
        # Trace fields on ScoringCandidate, not candidate.metadata
        assert "_matched_fields" not in merged[0].candidate.metadata
        assert "_retrieval_source" not in merged[0].candidate.metadata
        assert "_source_retrievers" not in merged[0].candidate.metadata
        # Trace fields are on ScoringCandidate
        assert merged[0].retrieval_source == "hybrid"
        assert merged[0].source_retrievers == ["keyword", "vector_placeholder"]
        assert len(merged[0].matched_fields) >= 1

    def test_corpus_candidate_metadata_clean(self):
        """Original corpus candidate.metadata must not be mutated by merge."""
        corpus_candidate = CandidateEvidence(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello world",
            cleaned_text="Hello world",
            raw_text_hash="abc123",
            metadata={},
        )
        kw = [ScoringCandidate(
            candidate=corpus_candidate,
            score=RetrievalScore(keyword_score=0.8, score_policy="token_frequency"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )]
        merger = HybridScoreMerger(alpha=0.5)
        merger.merge(kw, [])
        # Original corpus candidate.metadata is clean
        assert "_matched_fields" not in corpus_candidate.metadata
        assert "_retrieval_source" not in corpus_candidate.metadata
        assert "_source_retrievers" not in corpus_candidate.metadata


class TestNoNormalizeScores:
    """normalize_scores was removed — it was unused."""

    def test_normalize_scores_not_exported(self):
        from tracevault.retrieval import scoring
        assert not hasattr(scoring, "normalize_scores")


class TestScoringCandidateFromMerger:
    """Merger returns ScoringCandidate with trace fields."""

    def test_merged_is_scoring_candidate(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        merged = merger.merge(kw, [])
        assert isinstance(merged[0], ScoringCandidate)

    def test_merged_candidate_has_score(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        merged = merger.merge(kw, [])
        # hybrid_score = alpha * vector_score + (1-alpha) * keyword_score
        # = 0.5 * 0.0 + 0.5 * 0.8 = 0.4
        assert merged[0].score.hybrid_score == 0.4
        assert merged[0].candidate.score.hybrid_score == 0.4

    def test_merged_candidate_metadata_is_copy(self):
        """Merger creates a copy of candidate.metadata, not shared reference."""
        original_metadata = {"env": "prod"}
        s = _make_scoring(chunk_id="chunk_001", keyword_score=0.8)
        s.candidate.metadata = original_metadata
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([s], [])
        # Merged candidate has the metadata
        assert merged[0].candidate.metadata["env"] == "prod"
        # But it's a copy
        assert merged[0].candidate.metadata is not original_metadata


class TestTwoRunsNoStaleTrace:
    """Same ScoringCandidate reused across two merge runs — no stale trace."""

    def test_two_merges_no_stale(self):
        merger = HybridScoreMerger(alpha=0.5)
        kw = [_make_scoring(chunk_id="chunk_001", keyword_score=0.8)]
        vec = [_make_scoring(chunk_id="chunk_001", vector_score=0.6, score_policy="deterministic_placeholder", retrieval_source="vector_placeholder", source_retrievers=["vector_placeholder"])]

        merged1 = merger.merge(kw, vec)
        merged2 = merger.merge(kw, vec)

        # Both have hybrid source
        assert merged1[0].retrieval_source == "hybrid"
        assert merged2[0].retrieval_source == "hybrid"

        # Original ScoringCandidate trace fields unchanged
        assert kw[0].retrieval_source == "keyword"
        assert vec[0].retrieval_source == "vector_placeholder"

        # Merged candidates have clean metadata
        assert "_retrieval_source" not in merged1[0].candidate.metadata
        assert "_retrieval_source" not in merged2[0].candidate.metadata


class TestRetrievalResultTraceFromPipeline:
    """Pipeline-level: trace fields come from ScoringCandidate, not candidate.metadata."""

    def test_trace_has_retrieval_source(self):
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.trace.retrieval_source in ("keyword", "hybrid")

    def test_trace_has_matched_fields(self):
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.matched_fields) >= 1

    def test_trace_has_source_retrievers(self):
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.source_retrievers) >= 1

    def test_candidate_metadata_clean_after_pipeline(self):
        """Pipeline results should have clean candidate.metadata."""
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))

        run_specific_keys = ["_matched_fields", "_retrieval_source", "_source_retrievers"]
        for key in run_specific_keys:
            assert key not in corpus[0].metadata, f"{key} leaked into corpus metadata"

    def test_per_result_trace_contains_required_fields(self):
        """Per-result trace contains retrieval_source, matched_fields, etc."""
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest
        from tracevault.retrieval.pipeline import create_pipeline

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
        from tracevault.retrieval.models import RetrievalRequest, TextRetrievalPolicy
        from tracevault.retrieval.pipeline import create_pipeline

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
