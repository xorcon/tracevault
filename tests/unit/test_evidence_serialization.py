"""Tests for evidence pack JSON serialization.

Serialization must preserve all audit metadata for round-trip safety.
"""

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.models import (
    EvidenceBudget,
    EvidencePackRequest,
)
from tracevault.evidence.serialization import (
    deserialize_evidence_pack,
    deserialize_evidence_pack_trace,
    serialize_evidence_pack,
    serialize_evidence_pack_response,
)
from tracevault.retrieval.audit import build_response, rank_candidates
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
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


class TestSerializeEvidencePack:
    def test_serialize_produces_valid_json(self):
        import json

        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = json.loads(json_str)
        assert "items" in parsed
        assert "trace" in parsed

    def test_serialize_preserves_document_id(self):
        scorings = [_make_scoring(document_id="doc_abc")]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["items"][0]["document_id"] == "doc_abc"

    def test_serialize_preserves_chunk_id(self):
        scorings = [_make_scoring(chunk_id="chunk_abc")]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["items"][0]["chunk_id"] == "chunk_abc"

    def test_serialize_preserves_raw_text_hash(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["items"][0]["raw_text_hash"] == "abc123"

    def test_serialize_preserves_score_components(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        score = parsed["items"][0]["score"]
        assert score["keyword_score"] == 0.8
        assert score["vector_score"] == 0.6

    def test_serialize_preserves_rank(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["items"][0]["rank"] == 1

    def test_serialize_preserves_trace_metadata(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        trace = parsed["trace"]
        assert trace["pack_id"] != ""
        assert trace["retrieval_run_id"] == "run_001"
        assert trace["query"] == "test"
        assert trace["total_selected_items"] == 1

    def test_serialize_preserves_exclusions(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(3)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=1)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert len(parsed["trace"]["exclusions"]) == 2
        assert parsed["trace"]["exclusions"][0]["reason"] == "max_items_exceeded"

    def test_serialize_preserves_policies(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["trace"]["selection_policy"]["order_by"] == "retrieval_rank"
        assert parsed["trace"]["context_policy"]["include_raw_text"] is True

    def test_serialize_preserves_text_policy(self):
        from tracevault.retrieval.audit import build_response as br

        s = _make_scoring()
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=10,
            filters=None,
        )
        resp = br(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.raw_only(),
            filters=None,
        )
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert parsed["trace"]["text_policy"] == "RAW_ONLY"

    def test_serialize_preserves_applied_filters(self):
        s = _make_scoring()
        filt = MetadataFilter(document_id="doc_001")
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=10,
            filters=filt,
        )
        resp = build_response(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
            filters=filt,
        )
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack(result.evidence_pack)
        parsed = __import__("json").loads(json_str)
        assert "document_id=doc_001" in parsed["trace"]["applied_filters"]


class TestSerializeResponse:
    def test_serialize_response_produces_valid_json(self):
        import json

        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        json_str = serialize_evidence_pack_response(result)
        parsed = json.loads(json_str)
        assert "items" in parsed


class TestDeserializeEvidencePack:
    def test_deserialize_round_trip(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert len(restored.items) == 1
        assert restored.items[0].document_id == "doc_001"
        assert restored.items[0].chunk_id == "chunk_doc_001_0"
        assert restored.items[0].raw_text == "Hello world"
        assert restored.items[0].cleaned_text == "Hello world"

    def test_deserialize_preserves_score(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert restored.items[0].score.keyword_score == 0.8
        assert restored.items[0].score.vector_score == 0.6

    def test_deserialize_preserves_trace(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert restored.trace.pack_id == result.evidence_pack.trace.pack_id
        assert restored.trace.retrieval_run_id == "run_001"
        assert restored.trace.query == "test"

    def test_deserialize_preserves_exclusions(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(3)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=1)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert len(restored.trace.exclusions) == 2
        assert restored.trace.exclusions[0].reason == "max_items_exceeded"

    def test_deserialize_preserves_policies(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert restored.trace.selection_policy.order_by == "retrieval_rank"
        assert restored.trace.context_policy.include_raw_text is True

    def test_deserialize_preserves_text_policy(self):
        from tracevault.retrieval.audit import build_response as br

        s = _make_scoring()
        results = rank_candidates(
            candidates=[s],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=10,
            filters=None,
        )
        resp = br(
            results=results,
            query="test",
            retrieval_run_id="run_001",
            total_candidates=1,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.raw_only(),
            filters=None,
        )
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        restored = deserialize_evidence_pack(d)

        assert restored.trace.text_policy.mode == "RAW_ONLY"


class TestDeserializeTrace:
    def test_deserialize_trace_with_budget(self):
        trace = deserialize_evidence_pack_trace({
            "pack_id": "pack_001",
            "retrieval_run_id": "run_001",
            "query": "test",
            "query_hash": "qhash",
            "total_input_results": 1,
            "total_selected_items": 1,
            "total_excluded_items": 0,
            "exclusions": [],
            "selection_policy": {"order_by": "retrieval_rank", "deduplicate_by": "document_chunk"},
            "context_policy": {"include_raw_text": True, "include_cleaned_text": True},
            "budget": {"max_items": 5, "max_raw_chars": None, "max_cleaned_chars": None, "max_context_chars": None},
            "text_policy": "DUAL_CONTEXT",
            "applied_filters": [],
            "pack_run_id": "",
        })
        assert trace.budget.max_items == 5

    def test_deserialize_trace_without_budget(self):
        trace = deserialize_evidence_pack_trace({
            "pack_id": "pack_001",
            "retrieval_run_id": "run_001",
            "query": "test",
            "query_hash": "qhash",
            "total_input_results": 1,
            "total_selected_items": 1,
            "total_excluded_items": 0,
            "exclusions": [],
            "selection_policy": {"order_by": "retrieval_rank", "deduplicate_by": "document_chunk"},
            "context_policy": {"include_raw_text": True, "include_cleaned_text": True},
            "budget": None,
            "text_policy": "DUAL_CONTEXT",
            "applied_filters": [],
            "pack_run_id": "",
        })
        assert trace.budget is None


class TestNoRuntimeArtifacts:
    def test_serialization_creates_no_files(self):
        import os

        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        serialize_evidence_pack(result.evidence_pack)

        # No .db or .sqlite files created
        for root, _dirs, files in os.walk("."):
            for f in files:
                if f.endswith(".db") or f.endswith(".sqlite"):
                    raise AssertionError(f"Runtime artifact created: {os.path.join(root, f)}")
