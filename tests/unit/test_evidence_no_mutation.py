"""Tests that evidence pack builder does not mutate input objects.

RetrievalResponse, RetrievalResult, CandidateEvidence, and
CandidateEvidence.metadata must not be modified by the builder.
"""

import copy

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.models import (
    EvidenceBudget,
    EvidencePackRequest,
)
from tracevault.retrieval.audit import build_response, rank_candidates
from tracevault.retrieval.models import (
    CandidateEvidence,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)


def _make_scoring(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
    keyword_score=0.8,
    vector_score=0.6,
    metadata=None,
):
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
            score=RetrievalScore(
                keyword_score=keyword_score,
                vector_score=vector_score,
                hybrid_score=0.5 * vector_score + 0.5 * keyword_score,
                alpha=0.5,
                score_policy="hybrid",
            ),
            metadata=metadata or {},
        ),
        score=RetrievalScore(
            keyword_score=keyword_score,
            vector_score=vector_score,
            hybrid_score=0.5 * vector_score + 0.5 * keyword_score,
            alpha=0.5,
            score_policy="hybrid",
        ),
        matched_fields=["raw_text"],
        retrieval_source="hybrid",
        source_retrievers=["keyword", "vector"],
    )


def _make_response(scorings, retrieval_run_id="run_001"):
    results = rank_candidates(
        candidates=scorings,
        retrieval_run_id=retrieval_run_id,
        query_hash="qhash",
        top_k=10,
        filters=None,
    )
    return build_response(
        results=results,
        query="test",
        retrieval_run_id=retrieval_run_id,
        total_candidates=len(scorings),
        alpha=0.5,
        text_policy=TextRetrievalPolicy.dual_context(),
        filters=None,
    )


def _deep_copy_response(resp):
    """Deep copy a RetrievalResponse for comparison."""
    return copy.deepcopy(resp)


class TestNoMutationRetrievalResponse:
    def test_retrieval_response_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original = _deep_copy_response(resp)

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.retrieval_run_id == original.retrieval_run_id
        assert resp.query == original.query
        assert resp.query_hash == original.query_hash
        assert len(resp.results) == len(original.results)
        assert resp.alpha == original.alpha
        assert resp.text_policy.mode == original.text_policy.mode

    def test_retrieval_response_results_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original = _deep_copy_response(resp)

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        for i, r in enumerate(resp.results):
            orig_r = original.results[i]
            assert r.rank == orig_r.rank
            assert r.retrieval_run_id == orig_r.retrieval_run_id
            assert r.query_hash == orig_r.query_hash


class TestNoMutationCandidateEvidence:
    def test_candidate_raw_text_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original_raw = resp.results[0].candidate.raw_text

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].candidate.raw_text == original_raw

    def test_candidate_cleaned_text_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original_cleaned = resp.results[0].candidate.cleaned_text

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].candidate.cleaned_text == original_cleaned

    def test_candidate_metadata_not_mutated(self):
        s = _make_scoring(metadata={"env": "prod"})
        resp = _make_response([s])
        original_metadata = copy.deepcopy(resp.results[0].candidate.metadata)

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].candidate.metadata == original_metadata

    def test_candidate_score_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original_score = copy.deepcopy(resp.results[0].candidate.score.to_dict())

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].candidate.score.to_dict() == original_score


class TestNoMutationTrace:
    def test_retrieval_trace_not_mutated(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        original_trace = copy.deepcopy(resp.results[0].trace.to_dict())

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].trace.to_dict() == original_trace


class TestNoMutationWithBudget:
    def test_no_mutation_with_budget(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        resp = _make_response(scorings)
        original = _deep_copy_response(resp)

        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=3)
        builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        assert len(resp.results) == len(original.results)
        for i, r in enumerate(resp.results):
            orig_r = original.results[i]
            assert r.rank == orig_r.rank
            assert r.candidate.raw_text == orig_r.candidate.raw_text


class TestNoMutationWithDedup:
    def test_no_mutation_with_dedup(self):
        s1 = _make_scoring(chunk_id="chunk_001", keyword_score=0.9)
        s2 = _make_scoring(chunk_id="chunk_001", keyword_score=0.7)
        resp = _make_response([s1, s2])
        original = _deep_copy_response(resp)

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert len(resp.results) == len(original.results)


class TestNoMetadataPollution:
    def test_candidate_metadata_not_polluted_with_pack_fields(self):
        """CandidateEvidence.metadata must not be polluted with pack-specific metadata."""
        s = _make_scoring(metadata={"env": "prod"})
        resp = _make_response([s])

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        meta = resp.results[0].candidate.metadata
        assert "_pack_id" not in meta
        assert "_evidence_item" not in meta
        assert "_selected" not in meta
        assert "_excluded" not in meta
        assert "_rank" not in meta
        assert "_matched_fields" not in meta
        assert "_retrieval_source" not in meta
        assert "_source_retrievers" not in meta

    def test_only_original_metadata_present(self):
        s = _make_scoring(metadata={"env": "prod"})
        resp = _make_response([s])

        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        assert resp.results[0].candidate.metadata == {"env": "prod"}


class TestNoRuntimeArtifacts:
    def test_builder_creates_no_files(self):
        import os

        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        # No .db or .sqlite files created
        for root, _dirs, files in os.walk("."):
            for f in files:
                if f.endswith(".db") or f.endswith(".sqlite"):
                    raise AssertionError(f"Runtime artifact created: {os.path.join(root, f)}")

    def test_no_tracevault_runtime_state(self):
        """Builder must not create .tracevault/ runtime state."""
        import os

        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        builder.build(EvidencePackRequest(retrieval_response=resp))

        # Check no evidence pack runtime files
        tracevault_dir = ".tracevault"
        if os.path.exists(tracevault_dir):
            for root, _dirs, files in os.walk(tracevault_dir):
                for f in files:
                    if "evidence" in f.lower() and f.endswith(".json"):
                        raise AssertionError(f"Runtime evidence artifact: {os.path.join(root, f)}")


class TestEvidenceItemIsolation:
    def test_evidence_item_lists_are_independent(self):
        """Mutating source_retrievers on one item shouldn't affect the source."""
        s = _make_scoring()
        resp = _make_response([s])
        original_retrievers = list(resp.results[0].trace.source_retrievers)

        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        # Mutate the evidence item's list
        result.evidence_pack.items[0].source_retrievers.append("mutated")

        # Source should be unchanged
        assert resp.results[0].trace.source_retrievers == original_retrievers

    def test_evidence_item_matched_fields_independent(self):
        s = _make_scoring()
        resp = _make_response([s])
        original_fields = list(resp.results[0].trace.matched_fields)

        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        result.evidence_pack.items[0].matched_fields.append("mutated")
        assert resp.results[0].trace.matched_fields == original_fields

    def test_evidence_item_applied_filters_independent(self):
        s = _make_scoring()
        resp = _make_response([s])
        original_filters = list(resp.results[0].trace.applied_filters)

        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        result.evidence_pack.items[0].applied_filters.append("mutated")
        assert resp.results[0].trace.applied_filters == original_filters

    def test_evidence_item_candidate_metadata_independent(self):
        s = _make_scoring(metadata={"env": "prod"})
        resp = _make_response([s])
        original_meta = dict(resp.results[0].candidate.metadata)

        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        result.evidence_pack.items[0].candidate_metadata["new_key"] = "new_value"
        assert resp.results[0].candidate.metadata == original_meta

    def test_nested_candidate_metadata_is_deep_copied(self):
        """Nested dicts/lists in candidate_metadata must be deep-copied."""
        nested_meta = {"env": "prod", "tags": ["a", "b"], "config": {"key": "val"}}
        s = _make_scoring(metadata=nested_meta)
        resp = _make_response([s])

        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        # Mutate nested structures in the evidence item
        result.evidence_pack.items[0].candidate_metadata["tags"].append("c")
        result.evidence_pack.items[0].candidate_metadata["config"]["key"] = "mutated"

        # Original must be unchanged
        assert resp.results[0].candidate.metadata["tags"] == ["a", "b"]
        assert resp.results[0].candidate.metadata["config"]["key"] == "val"
