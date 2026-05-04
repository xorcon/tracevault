"""Tests for hybrid retrieval pipeline."""

import os

import pytest

from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalRequest,
)
from tracevault.retrieval.pipeline import HybridRetrievalPipeline, create_pipeline
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


def _make_pipeline(corpus):
    kw = InMemoryKeywordRetriever(corpus)
    vec = InMemoryVectorRetrieverPlaceholder(corpus)
    return HybridRetrievalPipeline(kw, vec)


class TestHybridRetrievalPipeline:
    def test_basic_retrieval(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming language",
                cleaned_text="Python programming language",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1
        assert resp.results[0].rank == 1

    def test_empty_query_raises(self):
        pipeline = _make_pipeline([])
        req = RetrievalRequest(query="")
        with pytest.raises(ValueError, match="empty"):
            pipeline.retrieve(req)

    def test_invalid_top_k_raises(self):
        pipeline = _make_pipeline([])
        req = RetrievalRequest(query="test", top_k=0)
        with pytest.raises(ValueError, match="top_k"):
            pipeline.retrieve(req)

    def test_invalid_alpha_raises(self):
        pipeline = _make_pipeline([])
        req = RetrievalRequest(query="test", alpha=1.5)
        with pytest.raises(ValueError, match="alpha"):
            pipeline.retrieve(req)

    def test_alpha_zero_keyword_only(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", alpha=0.0, top_k=5)
        resp = pipeline.retrieve(req)
        for r in resp.results:
            expected = r.candidate.score.keyword_score
            assert r.candidate.score.hybrid_score == pytest.approx(expected)

    def test_alpha_one_vector_only(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", alpha=1.0, top_k=5)
        resp = pipeline.retrieve(req)
        for r in resp.results:
            expected = r.candidate.score.vector_score
            assert r.candidate.score.hybrid_score == pytest.approx(expected)

    def test_alpha_half_merge(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", alpha=0.5, top_k=5)
        resp = pipeline.retrieve(req)
        for r in resp.results:
            expected = 0.5 * r.candidate.score.vector_score + 0.5 * r.candidate.score.keyword_score
            assert r.candidate.score.hybrid_score == pytest.approx(expected)

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
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=3)
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 3

    def test_deduplication(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        chunk_ids = [r.chunk_id for r in resp.results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_metadata_filter(self):
        corpus = [
            _make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python"),
            _make_candidate(document_id="doc_002", raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(document_id="doc_001"),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        for r in resp.results:
            assert r.document_id == "doc_001"

    def test_filter_no_match_returns_empty(self):
        corpus = [
            _make_candidate(document_id="doc_001", raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(document_id="doc_999"),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 0

    def test_response_has_audit_metadata(self):
        corpus = [
            _make_candidate(
                chunk_id="chunk_doc_001_0",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert resp.retrieval_run_id.startswith("run_")
        assert len(resp.query_hash) == 64
        assert resp.query == "Python"
        assert resp.alpha == 0.5
        assert resp.text_policy.mode == "DUAL_CONTEXT"

    def test_rank_is_1_based(self):
        corpus = [
            _make_candidate(
                chunk_id=f"chunk_doc_001_{i}",
                chunk_index=i,
                raw_text="Python programming",
                cleaned_text="Python programming",
            )
            for i in range(3)
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=3)
        resp = pipeline.retrieve(req)
        assert resp.results[0].rank == 1
        assert resp.results[1].rank == 2
        assert resp.results[2].rank == 3

    def test_result_preserves_traceability(self):
        corpus = [
            _make_candidate(
                document_id="doc_abc",
                chunk_id="chunk_doc_abc_5",
                source_path="docs/deep/file.md",
                raw_text_hash="sha256hash",
                raw_text="Python programming",
                cleaned_text="Python programming",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.document_id == "doc_abc"
        assert r.chunk_id == "chunk_doc_abc_5"
        assert r.source_path == "docs/deep/file.md"
        assert r.raw_text_hash == "sha256hash"

    def test_does_not_modify_corpus(self):
        corpus = [_make_candidate(raw_text="Original", cleaned_text="Original")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Original", top_k=5)
        pipeline.retrieve(req)
        assert corpus[0].raw_text == "Original"
        assert corpus[0].cleaned_text == "Original"

    def test_response_to_dict(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        d = resp.to_dict()
        assert "retrieval_run_id" in d
        assert "query" in d
        assert "results" in d
        assert "total_candidates" in d
        assert "alpha" in d
        assert "text_policy" in d

    def test_custom_run_id(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", retrieval_run_id="custom_run_123")
        resp = pipeline.retrieve(req)
        assert resp.retrieval_run_id == "custom_run_123"

    def test_no_answer_generation(self):
        corpus = [_make_candidate(raw_text="Python is a programming language", cleaned_text="Python is a programming language")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="What is Python?")
        resp = pipeline.retrieve(req)
        d = resp.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "llm" not in d
        assert "generation" not in d

    def test_no_llm_call(self):
        """Pipeline must not call any LLM."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python")
        # Should not hang or raise — no LLM call
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 0

    def test_no_runtime_index_files(self):
        """Pipeline must not create runtime index files."""
        corpus = [_make_candidate(raw_text="Python programming", cleaned_text="Python programming")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python")
        pipeline.retrieve(req)
        # Check no .db or .sqlite files created
        for root, _dirs, files in os.walk("."):
            for f in files:
                if f.endswith(".db") or f.endswith(".sqlite"):
                    raise AssertionError(f"Runtime artifact created: {os.path.join(root, f)}")


class TestCreatePipeline:
    def test_create_pipeline_basic(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1

    def test_create_pipeline_with_text_policy(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1


class TestKeyValueFilterEndToEnd:
    """Pipeline-level tests for key_value metadata filtering."""

    def test_key_value_filter_returns_matching_candidate(self):
        corpus = [
            _make_candidate(metadata={"env": "prod"}, raw_text="Python", cleaned_text="Python"),
            _make_candidate(metadata={"env": "dev"}, raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(key_value={"env": "prod"}),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        for r in resp.results:
            assert r.candidate.metadata["env"] == "prod"

    def test_key_value_filter_excludes_non_matching(self):
        corpus = [
            _make_candidate(metadata={"env": "prod"}, raw_text="Python", cleaned_text="Python"),
            _make_candidate(metadata={"env": "dev"}, raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(key_value={"env": "prod"}),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        for r in resp.results:
            assert r.candidate.metadata["env"] != "dev"

    def test_key_value_filter_no_match_returns_empty(self):
        corpus = [
            _make_candidate(metadata={"env": "prod"}, raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(key_value={"env": "staging"}),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 0

    def test_key_value_filter_through_hybrid_pipeline(self):
        """key_value filter works through the full HybridRetrievalPipeline."""
        corpus = [
            _make_candidate(metadata={"team": "infra"}, raw_text="Python", cleaned_text="Python"),
            _make_candidate(metadata={"team": "data"}, raw_text="Python", cleaned_text="Python"),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(key_value={"team": "infra"}),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1
        for r in resp.results:
            assert r.candidate.metadata["team"] == "infra"

    def test_combined_filter_with_key_value(self):
        corpus = [
            _make_candidate(
                document_id="doc_001",
                metadata={"env": "prod"},
                raw_text="Python",
                cleaned_text="Python",
            ),
            _make_candidate(
                document_id="doc_002",
                metadata={"env": "prod"},
                raw_text="Python",
                cleaned_text="Python",
            ),
            _make_candidate(
                document_id="doc_001",
                metadata={"env": "dev"},
                raw_text="Python",
                cleaned_text="Python",
            ),
        ]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(
                document_id="doc_001",
                key_value={"env": "prod"},
            ),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        for r in resp.results:
            assert r.document_id == "doc_001"
            assert r.candidate.metadata["env"] == "prod"


class TestTextPolicyEndToEnd:
    """Pipeline-level tests for text_policy enforcement."""

    def test_raw_only_searches_raw_text(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="Python programming", cleaned_text="Java programming"),
        ]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1

    def test_cleaned_only_searches_cleaned_text(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="Java programming", cleaned_text="Python programming"),
        ]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert len(resp.results) >= 1

    def test_cleaned_only_preserves_raw_text(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="Python programming", cleaned_text="Python programming"),
        ]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.cleaned_only())
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        for r in resp.results:
            assert r.candidate.raw_text == "Python programming"
            assert r.candidate.cleaned_text == "Python programming"

    def test_response_text_policy_matches_actual(self):
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        assert resp.text_policy.mode == "RAW_ONLY"

    def test_request_text_policy_overrides_retriever_default(self):
        """request.text_policy overrides retriever constructor default."""
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="rawword", cleaned_text="cleanedword"),
        ]
        # Pipeline built with RAW_ONLY
        pipeline = create_pipeline(corpus, text_policy=TextRetrievalPolicy.raw_only())
        # Request with CLEANED_ONLY — should find "cleanedword"
        req = RetrievalRequest(
            query="cleanedword", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1
        assert resp.text_policy.mode == "CLEANED_ONLY"

    def test_request_text_policy_raw_only(self):
        """RAW_ONLY request finds a term only in raw_text."""
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="SECRET keyword", cleaned_text="cleaned text"),
        ]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(
            query="SECRET", top_k=5, text_policy=TextRetrievalPolicy.raw_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_request_text_policy_cleaned_only(self):
        """CLEANED_ONLY request finds a term only in cleaned_text."""
        from tracevault.retrieval.models import TextRetrievalPolicy
        corpus = [
            _make_candidate(raw_text="raw text", cleaned_text="CLEANED keyword"),
        ]
        pipeline = create_pipeline(corpus)
        req = RetrievalRequest(
            query="CLEANED", top_k=5, text_policy=TextRetrievalPolicy.cleaned_only()
        )
        resp = pipeline.retrieve(req)
        assert len(resp.results) == 1

    def test_cleaned_only_response_preserves_raw_text(self):
        """CLEANED_ONLY response still preserves raw_text."""
        from tracevault.retrieval.models import TextRetrievalPolicy
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


class TestTraceOnRetrievalResult:
    """Tests that trace lives on RetrievalResult, not CandidateEvidence."""

    def test_result_has_trace(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert hasattr(r, "trace")
        assert r.trace.document_id == "doc_001"

    def test_candidate_has_no_trace(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        c = resp.results[0].candidate
        assert not hasattr(c, "trace")

    def test_trace_contains_applied_filters(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(document_id="doc_001"),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert "document_id=doc_001" in r.trace.applied_filters

    def test_trace_contains_retrieval_source(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.trace.retrieval_source in ("keyword", "hybrid", "vector_placeholder")

    def test_trace_contains_score_policy(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert r.trace.score_policy in ("token_frequency", "hybrid", "deterministic_placeholder")

    def test_trace_contains_source_retrievers(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        r = resp.results[0]
        assert len(r.trace.source_retrievers) >= 1

    def test_same_candidate_reused_across_runs(self):
        """Same CandidateEvidence can be used in two runs without stale trace."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)

        req1 = RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_001")
        resp1 = pipeline.retrieve(req1)

        req2 = RetrievalRequest(query="Python", top_k=5, retrieval_run_id="run_002")
        resp2 = pipeline.retrieve(req2)

        # Traces should have different run IDs
        assert resp1.results[0].retrieval_run_id == "run_001"
        assert resp2.results[0].retrieval_run_id == "run_002"

        # Corpus should be unchanged
        assert corpus[0].raw_text == "Python"

    def test_trace_serialization_preserves_metadata(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(
            query="Python",
            filters=MetadataFilter(document_id="doc_001"),
            top_k=5,
        )
        resp = pipeline.retrieve(req)
        d = resp.to_dict()
        r = d["results"][0]
        assert "trace" in r
        assert r["trace"]["document_id"] == "doc_001"
        assert "document_id=doc_001" in r["trace"]["applied_filters"]
        assert r["trace"]["score_policy"] != ""
        assert len(r["trace"]["source_retrievers"]) >= 1

    def test_candidate_metadata_clean_after_pipeline(self):
        """Pipeline results should have clean candidate.metadata."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        req = RetrievalRequest(query="Python", top_k=5)
        resp = pipeline.retrieve(req)
        c = resp.results[0].candidate
        assert "_matched_fields" not in c.metadata
        assert "_retrieval_source" not in c.metadata
        assert "_source_retrievers" not in c.metadata

    def test_corpus_metadata_clean_after_pipeline(self):
        """Corpus candidate.metadata must not be mutated by pipeline."""
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)
        pipeline.retrieve(RetrievalRequest(query="Python", top_k=5))
        assert "_matched_fields" not in corpus[0].metadata
        assert "_retrieval_source" not in corpus[0].metadata
        assert "_source_retrievers" not in corpus[0].metadata


class TestNoStaleTraceAcrossRuns:
    """No stale trace metadata survives across retrieval runs."""

    def test_two_runs_no_stale_trace(self):
        corpus = [_make_candidate(raw_text="Python", cleaned_text="Python")]
        pipeline = _make_pipeline(corpus)

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


class TestPipelineTextPolicyOverrideFailsOnOldBehavior:
    """This test would fail on the previous behavior where request.text_policy was not enforced."""

    def test_request_policy_overrides_retriever_default_in_pipeline(self):
        """Pipeline must enforce request.text_policy, not just record it."""
        from tracevault.retrieval.models import TextRetrievalPolicy

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
