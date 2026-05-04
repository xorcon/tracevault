"""Regression tests for retrieval interface contract bugfix (PR #6).

Two bugs fixed:
1. Pipeline read self.keyword_retriever.text_policy — AttributeError if a
   custom keyword retriever didn't define that attribute. Now reads
   self.default_text_policy.
2. Scoring merger hardcoded "keyword", "vector_placeholder", "token_frequency",
   "deterministic_placeholder". Now derives from actual ScoringCandidate fields.
"""

from tracevault.retrieval.audit import build_response, rank_candidates
from tracevault.retrieval.interfaces import KeywordRetriever
from tracevault.retrieval.models import (
    CandidateEvidence,
    RetrievalRequest,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)
from tracevault.retrieval.pipeline import HybridRetrievalPipeline
from tracevault.retrieval.scoring import HybridScoreMerger
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


# ---------------------------------------------------------------------------
# P1 — Pipeline text_policy contract regression
# ---------------------------------------------------------------------------

class _MockKeywordRetriever(KeywordRetriever):
    """Custom keyword retriever without a text_policy attribute.

    Simulates a retriever that satisfies the KeywordRetriever protocol but
    does not define a constructor-time text_policy attribute — the exact
    scenario that caused AttributeError before PR #6.
    """

    source_type = "custom_keyword"

    def __init__(self, corpus):
        self.corpus = corpus
        self.received_text_policy = None

    def retrieve(
        self,
        query,
        top_k=5,
        filters=None,
        text_policy=None,
    ):
        self.received_text_policy = text_policy
        results = []
        for c in self.corpus:
            if query.lower() in c.raw_text.lower():
                results.append(
                    ScoringCandidate(
                        candidate=c,
                        score=RetrievalScore(
                            keyword_score=0.8,
                            score_policy="custom_keyword_policy",
                        ),
                        matched_fields=["raw_text"],
                        retrieval_source="custom_keyword",
                        source_retrievers=["custom_keyword"],
                    )
                )
        return results


class TestPipelineTextPolicyContract:
    """P1: Pipeline must use default_text_policy, not keyword_retriever.text_policy."""

    def _make_pipeline_with_mock_kw(self, corpus, default_text_policy=None):
        kw = _MockKeywordRetriever(corpus)
        vec = InMemoryVectorRetrieverPlaceholder(corpus)
        return HybridRetrievalPipeline(
            keyword_retriever=kw,
            vector_retriever=vec,
            default_text_policy=default_text_policy,
        )

    def test_no_attribute_error_with_custom_retriever_no_text_policy(self):
        """Custom retriever without text_policy attr must not raise AttributeError."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(query="Python", top_k=5, text_policy=None)
        # Before fix: AttributeError on self.keyword_retriever.text_policy
        resp = pipeline.retrieve(req)
        assert resp is not None

    def test_custom_retriever_receives_effective_text_policy_when_request_none(self):
        """When request.text_policy is None, retriever receives pipeline.default_text_policy.

        The pipeline computes effective_text_policy = request.text_policy or
        pipeline.default_text_policy. The same effective policy is passed to
        the keyword retriever and reported in the response — no audit mismatch.
        """
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(query="Python", top_k=5, text_policy=None)
        resp = pipeline.retrieve(req)

        # Retriever receives the pipeline default, not None
        assert pipeline.keyword_retriever.received_text_policy is not None
        assert pipeline.keyword_retriever.received_text_policy.mode == "DUAL_CONTEXT"

        # Response reports the same effective policy
        assert resp.text_policy.mode == "DUAL_CONTEXT"
        assert (
            pipeline.keyword_retriever.received_text_policy.mode
            == resp.text_policy.mode
        )

    def test_response_text_policy_equals_pipeline_default(self):
        """Response.text_policy equals pipeline.default_text_policy when request has none."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(query="Python", top_k=5, text_policy=None)
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "DUAL_CONTEXT"

    def test_request_text_policy_overrides_pipeline_default(self):
        """request.text_policy overrides pipeline.default_text_policy."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(
            query="Python",
            top_k=5,
            text_policy=TextRetrievalPolicy.raw_only(),
        )
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "RAW_ONLY"

    def test_custom_retriever_receives_request_text_policy(self):
        """Custom retriever receives request.text_policy, not pipeline default."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(
            query="Python",
            top_k=5,
            text_policy=TextRetrievalPolicy.cleaned_only(),
        )
        pipeline.retrieve(req)
        assert pipeline.keyword_retriever.received_text_policy is not None
        assert pipeline.keyword_retriever.received_text_policy.mode == "CLEANED_ONLY"

    def test_response_text_policy_equals_request_text_policy(self):
        """Response.text_policy equals request.text_policy when provided."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(corpus)
        req = RetrievalRequest(
            query="Python",
            top_k=5,
            text_policy=TextRetrievalPolicy.raw_only(),
        )
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "RAW_ONLY"

    def test_custom_default_text_policy_used_when_request_none(self):
        """Pipeline with custom default_text_policy uses it when request has none."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = self._make_pipeline_with_mock_kw(
            corpus, default_text_policy=TextRetrievalPolicy.raw_only()
        )
        req = RetrievalRequest(query="Python", top_k=5, text_policy=None)
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "RAW_ONLY"


# ---------------------------------------------------------------------------
# P2 — Scoring merger provenance contract regression
# ---------------------------------------------------------------------------

class TestScoringCustomProvenance:
    """P2: Merger must preserve custom retrieval_source / source_retrievers / score_policy."""

    def test_vector_only_merge_preserves_custom_vector_provenance(self):
        """Vector-only merge preserves custom vector source, not vector_placeholder."""
        vec = [
            _make_scoring(
                chunk_id="chunk_001",
                vector_score=0.7,
                score_policy="custom_vector_policy",
                retrieval_source="custom_vector",
                source_retrievers=["custom_vector"],
            )
        ]
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([], vec)

        assert len(merged) == 1
        assert merged[0].retrieval_source == "custom_vector"
        assert merged[0].source_retrievers == ["custom_vector"]
        assert merged[0].score.score_policy == "custom_vector_policy"
        # No hardcoded placeholder leaks
        assert "vector_placeholder" not in merged[0].retrieval_source
        assert "vector_placeholder" not in merged[0].source_retrievers
        assert "deterministic_placeholder" not in merged[0].score.score_policy

    def test_hybrid_keyword_custom_vector_merge_provenance(self):
        """Hybrid merge of keyword + custom vector preserves both sources."""
        kw = [
            _make_scoring(
                chunk_id="chunk_001",
                keyword_score=0.8,
                score_policy="token_frequency",
                retrieval_source="keyword",
                source_retrievers=["keyword"],
            )
        ]
        vec = [
            _make_scoring(
                chunk_id="chunk_001",
                vector_score=0.6,
                score_policy="custom_vector_policy",
                retrieval_source="custom_vector",
                source_retrievers=["custom_vector"],
            )
        ]
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge(kw, vec)

        assert len(merged) == 1
        assert merged[0].retrieval_source == "hybrid"
        assert merged[0].source_retrievers == ["keyword", "custom_vector"]
        assert merged[0].score.score_policy == "hybrid"
        # No hardcoded placeholder leaks
        assert "vector_placeholder" not in merged[0].source_retrievers

    def test_keyword_only_merge_preserves_custom_keyword_provenance(self):
        """Keyword-only merge preserves custom keyword source."""
        kw = [
            _make_scoring(
                chunk_id="chunk_001",
                keyword_score=0.8,
                score_policy="custom_keyword_policy",
                retrieval_source="custom_keyword",
                source_retrievers=["custom_keyword"],
            )
        ]
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge(kw, [])

        assert len(merged) == 1
        assert merged[0].retrieval_source == "custom_keyword"
        assert merged[0].source_retrievers == ["custom_keyword"]
        assert merged[0].score.score_policy == "custom_keyword_policy"

    def test_merge_fallback_when_source_retrievers_empty(self):
        """When source_retrievers is empty, merger falls back to [retrieval_source]."""
        s = ScoringCandidate(
            candidate=CandidateEvidence(
                document_id="doc_001",
                chunk_id="chunk_001",
                chunk_index=0,
                source_path="docs/test.md",
                source_type="md",
                raw_text="Hello",
                cleaned_text="Hello",
                raw_text_hash="abc",
                metadata={},
            ),
            score=RetrievalScore(
                keyword_score=0.8,
                score_policy="custom_policy",
            ),
            matched_fields=["raw_text"],
            retrieval_source="custom_source",
            source_retrievers=[],
        )
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([s], [])

        assert merged[0].source_retrievers == ["custom_source"]

    def test_merge_fallback_when_source_retrievers_none(self):
        """When source_retrievers is None, merger falls back to [retrieval_source]."""
        s = ScoringCandidate(
            candidate=CandidateEvidence(
                document_id="doc_001",
                chunk_id="chunk_001",
                chunk_index=0,
                source_path="docs/test.md",
                source_type="md",
                raw_text="Hello",
                cleaned_text="Hello",
                raw_text_hash="abc",
                metadata={},
            ),
            score=RetrievalScore(
                keyword_score=0.8,
                score_policy="custom_policy",
            ),
            matched_fields=["raw_text"],
            retrieval_source="custom_source",
            source_retrievers=None,
        )
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge([s], [])

        assert merged[0].source_retrievers == ["custom_source"]

    def test_hybrid_deduplicates_source_retrievers(self):
        """Hybrid merge deduplicates overlapping source_retrievers."""
        kw = [
            _make_scoring(
                chunk_id="chunk_001",
                keyword_score=0.8,
                retrieval_source="shared",
                source_retrievers=["shared"],
            )
        ]
        vec = [
            _make_scoring(
                chunk_id="chunk_001",
                vector_score=0.6,
                retrieval_source="shared",
                source_retrievers=["shared"],
            )
        ]
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge(kw, vec)

        assert merged[0].source_retrievers == ["shared"]


# ---------------------------------------------------------------------------
# P3 — Downstream traceability of custom provenance
# ---------------------------------------------------------------------------

class TestCustomProvenanceTraceability:
    """P3: RetrievalTrace source_retrievers preserves custom provenance downstream."""

    def test_rank_candidates_preserves_custom_source_retrievers(self):
        """rank_candidates passes through custom source_retrievers in trace."""
        s = ScoringCandidate(
            candidate=CandidateEvidence(
                document_id="doc_001",
                chunk_id="chunk_001",
                chunk_index=0,
                source_path="docs/test.md",
                source_type="md",
                raw_text="Hello",
                cleaned_text="Hello",
                raw_text_hash="abc",
                score=RetrievalScore(
                    keyword_score=0.8,
                    score_policy="custom_vector_policy",
                ),
                metadata={},
            ),
            score=RetrievalScore(
                keyword_score=0.8,
                score_policy="custom_vector_policy",
            ),
            matched_fields=["raw_text"],
            retrieval_source="custom_vector",
            source_retrievers=["custom_vector"],
        )
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=5,
            filters=None,
        )
        assert results[0].trace.source_retrievers == ["custom_vector"]
        assert results[0].trace.retrieval_source == "custom_vector"
        assert results[0].trace.score_policy == "custom_vector_policy"

    def test_build_response_preserves_custom_provenance_in_trace(self):
        """Full rank_candidates -> build_response path preserves custom provenance."""
        s = ScoringCandidate(
            candidate=CandidateEvidence(
                document_id="doc_001",
                chunk_id="chunk_001",
                chunk_index=0,
                source_path="docs/test.md",
                source_type="md",
                raw_text="Hello",
                cleaned_text="Hello",
                raw_text_hash="abc",
                score=RetrievalScore(
                    keyword_score=0.5,
                    vector_score=0.6,
                    score_policy="custom_vector_policy",
                ),
                metadata={},
            ),
            score=RetrievalScore(
                keyword_score=0.5,
                vector_score=0.6,
                score_policy="custom_vector_policy",
            ),
            matched_fields=["raw_text"],
            retrieval_source="custom_vector",
            source_retrievers=["custom_vector"],
        )
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=5,
            filters=None,
        )
        resp = build_response(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=None,
        )
        trace = resp.results[0].trace
        assert trace.source_retrievers == ["custom_vector"]
        assert trace.retrieval_source == "custom_vector"
        assert trace.score_policy == "custom_vector_policy"

    def test_hybrid_merge_traceability_through_full_path(self):
        """Custom vector + keyword hybrid provenance survives full audit path."""
        kw = [
            _make_scoring(
                chunk_id="chunk_001",
                keyword_score=0.8,
                score_policy="token_frequency",
                retrieval_source="keyword",
                source_retrievers=["keyword"],
            )
        ]
        vec = [
            _make_scoring(
                chunk_id="chunk_001",
                vector_score=0.6,
                score_policy="custom_vector_policy",
                retrieval_source="custom_vector",
                source_retrievers=["custom_vector"],
            )
        ]
        merger = HybridScoreMerger(alpha=0.5)
        merged = merger.merge(kw, vec)

        results = rank_candidates(
            candidates=merged,
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=5,
            filters=None,
        )
        resp = build_response(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=None,
        )
        trace = resp.results[0].trace
        assert trace.retrieval_source == "hybrid"
        assert trace.source_retrievers == ["keyword", "custom_vector"]
        assert trace.score_policy == "hybrid"

    def test_serialization_preserves_custom_provenance(self):
        """to_dict serialization preserves custom source_retrievers."""
        s = ScoringCandidate(
            candidate=CandidateEvidence(
                document_id="doc_001",
                chunk_id="chunk_001",
                chunk_index=0,
                source_path="docs/test.md",
                source_type="md",
                raw_text="Hello",
                cleaned_text="Hello",
                raw_text_hash="abc",
                score=RetrievalScore(
                    keyword_score=0.8,
                    score_policy="custom_vector_policy",
                ),
                metadata={},
            ),
            score=RetrievalScore(
                keyword_score=0.8,
                score_policy="custom_vector_policy",
            ),
            matched_fields=["raw_text"],
            retrieval_source="custom_vector",
            source_retrievers=["custom_vector"],
        )
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=5,
            filters=None,
        )
        resp = build_response(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=None,
        )
        d = resp.to_dict()
        trace_dict = d["results"][0]["trace"]
        assert trace_dict["source_retrievers"] == ["custom_vector"]
        assert trace_dict["retrieval_source"] == "custom_vector"
        assert trace_dict["score_policy"] == "custom_vector_policy"
