"""Tests for evidence pack determinism.

Same input and same policies must produce the same EvidencePack.
"""

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidencePackRequest,
    EvidenceSelectionPolicy,
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
            metadata={},
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


class TestDeterministicPackId:
    def test_same_input_same_pack_id(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert r1.evidence_pack.trace.pack_id == r2.evidence_pack.trace.pack_id

    def test_different_run_id_different_pack_id(self):
        scorings = [_make_scoring()]
        resp1 = _make_response(scorings, retrieval_run_id="run_001")
        resp2 = _make_response(scorings, retrieval_run_id="run_002")
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp1))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp2))

        assert r1.evidence_pack.trace.pack_id != r2.evidence_pack.trace.pack_id


class TestDeterministicOrdering:
    def test_same_ordering_across_runs(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp))

        ids1 = [i.chunk_id for i in r1.evidence_pack.items]
        ids2 = [i.chunk_id for i in r2.evidence_pack.items]
        assert ids1 == ids2


class TestOrderSensitivePackId:
    """pack_id must change when final evidence order changes."""

    def test_pack_id_changes_when_order_changes(self):
        """Same selected items in different order must produce different pack_id."""
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()

        # Same items, different order
        order_a = [("doc_001", "chunk_001"), ("doc_002", "chunk_002")]
        order_b = [("doc_002", "chunk_002"), ("doc_001", "chunk_001")]

        id_a = compute_pack_id("run_001", "qhash", order_a, sel, ctx, None)
        id_b = compute_pack_id("run_001", "qhash", order_b, sel, ctx, None)

        assert id_a != id_b, "pack_id must differ when item order differs"

    def test_pack_id_same_when_order_same(self):
        """Same items in same order must produce same pack_id."""
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()
        order = [("doc_001", "chunk_001"), ("doc_002", "chunk_002")]

        id_a = compute_pack_id("run_001", "qhash", order, sel, ctx, None)
        id_b = compute_pack_id("run_001", "qhash", order, sel, ctx, None)

        assert id_a == id_b


class TestDeterministicDedup:
    def test_same_dedup_result(self):
        s1 = _make_scoring(chunk_id="chunk_001", keyword_score=0.9)
        s2 = _make_scoring(chunk_id="chunk_001", keyword_score=0.7)
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert [i.chunk_id for i in r1.evidence_pack.items] == [i.chunk_id for i in r2.evidence_pack.items]


class TestDeterministicBudget:
    def test_same_budget_exclusion(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=3)

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        selected1 = [i.chunk_id for i in r1.evidence_pack.items]
        selected2 = [i.chunk_id for i in r2.evidence_pack.items]
        assert selected1 == selected2

        excluded1 = [(e.document_id, e.chunk_id) for e in r1.evidence_pack.trace.exclusions]
        excluded2 = [(e.document_id, e.chunk_id) for e in r2.evidence_pack.trace.exclusions]
        assert excluded1 == excluded2


class TestDeterministicContext:
    def test_same_context_string(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert r1.evidence_pack.context == r2.evidence_pack.context


class TestDeterministicWithPolicy:
    def test_same_policy_same_result(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        sel = EvidenceSelectionPolicy(deduplicate_by="raw_text_hash")

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp, selection_policy=sel))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp, selection_policy=sel))

        assert r1.evidence_pack.trace.pack_id == r2.evidence_pack.trace.pack_id


class TestNoWallClockTimestamps:
    def test_no_timestamp_in_pack(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        # Check no datetime-like fields
        trace = d["trace"]
        assert "created_at" not in trace
        assert "timestamp" not in trace
        assert "built_at" not in trace


class TestNoRandomUuids:
    def test_pack_id_is_deterministic_not_random(self):
        """pack_id should be deterministic, not a random UUID."""
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp))

        # If pack_id were a random UUID, these would differ
        assert r1.evidence_pack.trace.pack_id == r2.evidence_pack.trace.pack_id

    def test_pack_run_id_injected_not_random(self):
        """pack_run_id should come from the request, not be auto-generated."""
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()

        r1 = builder.build(EvidencePackRequest(retrieval_response=resp, pack_run_id="injected_id"))
        r2 = builder.build(EvidencePackRequest(retrieval_response=resp, pack_run_id="injected_id"))

        assert r1.evidence_pack.trace.pack_run_id == "injected_id"
        assert r2.evidence_pack.trace.pack_run_id == "injected_id"
