"""Tests for evidence pack traceability — all required fields preserved."""

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.models import EvidencePackRequest
from tracevault.retrieval.audit import build_response, rank_candidates
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)


def _make_scoring_full(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
    chunk_index=0,
    source_path="docs/test.md",
    source_type="md",
    raw_text="Hello world",
    cleaned_text="Hello world",
    raw_text_hash="abc123",
    cleaned_text_hash="def456",
    keyword_score=0.8,
    vector_score=0.6,
    hybrid_score=0.7,
    alpha=0.6,
    score_policy="hybrid",
    matched_fields=None,
    retrieval_source="hybrid",
    source_retrievers=None,
    metadata=None,
):
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
                vector_score=vector_score,
                hybrid_score=hybrid_score,
                alpha=alpha,
                score_policy=score_policy,
            ),
            metadata=metadata or {},
        ),
        score=RetrievalScore(
            keyword_score=keyword_score,
            vector_score=vector_score,
            hybrid_score=hybrid_score,
            alpha=alpha,
            score_policy=score_policy,
        ),
        matched_fields=matched_fields or ["raw_text", "cleaned_text"],
        retrieval_source=retrieval_source,
        source_retrievers=source_retrievers or ["keyword", "vector"],
    )


def _make_response(scorings, query="test", retrieval_run_id="run_001", filters=None, text_policy=None):
    results = rank_candidates(
        candidates=scorings,
        retrieval_run_id=retrieval_run_id,
        query_hash="qhash",
        top_k=10,
        filters=filters,
    )
    return build_response(
        results=results,
        query=query,
        retrieval_run_id=retrieval_run_id,
        total_candidates=len(scorings),
        alpha=0.5,
        text_policy=text_policy or TextRetrievalPolicy.dual_context(),
        filters=filters,
    )


class TestTraceabilityFields:
    """Every required traceability field must survive the evidence pack pipeline."""

    def test_document_id_preserved(self):
        s = _make_scoring_full(document_id="doc_traceable")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].document_id == "doc_traceable"

    def test_chunk_id_preserved(self):
        s = _make_scoring_full(chunk_id="chunk_traceable")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].chunk_id == "chunk_traceable"

    def test_chunk_index_preserved(self):
        s = _make_scoring_full(chunk_index=5)
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].chunk_index == 5

    def test_source_path_preserved(self):
        s = _make_scoring_full(source_path="docs/deep/nested/file.md")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].source_path == "docs/deep/nested/file.md"

    def test_source_type_preserved(self):
        s = _make_scoring_full(source_type="txt")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].source_type == "txt"

    def test_raw_text_preserved(self):
        s = _make_scoring_full(raw_text="Source of truth text", cleaned_text="Source of truth text")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].raw_text == "Source of truth text"

    def test_cleaned_text_preserved(self):
        s = _make_scoring_full(raw_text="raw", cleaned_text="cleaned version")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].cleaned_text == "cleaned version"

    def test_raw_text_hash_preserved(self):
        s = _make_scoring_full(raw_text_hash="sha256raw")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].raw_text_hash == "sha256raw"

    def test_cleaned_text_hash_preserved(self):
        s = _make_scoring_full(cleaned_text_hash="sha256cleaned")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].cleaned_text_hash == "sha256cleaned"

    def test_retrieval_run_id_preserved(self):
        s = _make_scoring_full()
        resp = _make_response([s], retrieval_run_id="run_traceable")
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].retrieval_run_id == "run_traceable"

    def test_query_hash_preserved(self):
        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].query_hash == "qhash"

    def test_retrieval_source_preserved(self):
        s = _make_scoring_full(retrieval_source="keyword", source_retrievers=["keyword"])
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].retrieval_source == "keyword"

    def test_source_retrievers_preserved(self):
        s = _make_scoring_full(source_retrievers=["keyword", "custom_vector"])
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].source_retrievers == ["keyword", "custom_vector"]

    def test_matched_fields_preserved(self):
        s = _make_scoring_full(matched_fields=["raw_text", "cleaned_text"])
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].matched_fields == ["raw_text", "cleaned_text"]

    def test_score_keyword_preserved(self):
        s = _make_scoring_full(keyword_score=0.85)
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].score.keyword_score == 0.85

    def test_score_vector_preserved(self):
        s = _make_scoring_full(vector_score=0.72)
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].score.vector_score == 0.72

    def test_score_hybrid_preserved(self):
        s = _make_scoring_full(hybrid_score=0.78)
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].score.hybrid_score == 0.78

    def test_score_alpha_preserved(self):
        s = _make_scoring_full(alpha=0.7)
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].score.alpha == 0.7

    def test_score_policy_preserved(self):
        s = _make_scoring_full(score_policy="custom_policy")
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].score.score_policy == "custom_policy"

    def test_rank_preserved(self):
        scorings = [
            _make_scoring_full(chunk_id="chunk_001", keyword_score=0.9),
            _make_scoring_full(chunk_id="chunk_002", keyword_score=0.7),
        ]
        resp = _make_response(scorings)
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].rank == 1
        assert result.evidence_pack.items[1].rank == 2

    def test_text_policy_preserved(self):
        s = _make_scoring_full()
        resp = _make_response([s], text_policy=TextRetrievalPolicy.raw_only())
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].text_policy.mode == "RAW_ONLY"

    def test_applied_filters_preserved(self):
        s = _make_scoring_full()
        filt = MetadataFilter(document_id="doc_001", source_type="md")
        resp = _make_response([s], filters=filt)
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert "document_id=doc_001" in result.evidence_pack.items[0].applied_filters

    def test_candidate_metadata_preserved(self):
        s = _make_scoring_full(metadata={"env": "prod", "team": "infra"})
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.items[0].candidate_metadata == {"env": "prod", "team": "infra"}


class TestTraceLevelTraceability:
    """Trace-level fields must also be preserved."""

    def test_trace_pack_id_not_empty(self):
        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.pack_id != ""

    def test_trace_retrieval_run_id(self):
        s = _make_scoring_full()
        resp = _make_response([s], retrieval_run_id="run_trace")
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.retrieval_run_id == "run_trace"

    def test_trace_query(self):
        s = _make_scoring_full()
        resp = _make_response([s], query="trace query")
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.query == "trace query"

    def test_trace_query_hash(self):
        import hashlib

        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        # query_hash is computed by build_response from the query string
        expected_hash = hashlib.sha256("test".encode("utf-8")).hexdigest()
        assert result.evidence_pack.trace.query_hash == expected_hash

    def test_trace_total_input_results(self):
        scorings = [
            _make_scoring_full(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        resp = _make_response(scorings)
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.total_input_results == 5

    def test_trace_total_selected_items(self):
        scorings = [
            _make_scoring_full(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(3)
        ]
        resp = _make_response(scorings)
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.total_selected_items == 3

    def test_trace_text_policy(self):
        s = _make_scoring_full()
        resp = _make_response([s], text_policy=TextRetrievalPolicy.cleaned_only())
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert result.evidence_pack.trace.text_policy.mode == "CLEANED_ONLY"

    def test_trace_applied_filters(self):
        s = _make_scoring_full()
        filt = MetadataFilter(document_id="doc_001")
        resp = _make_response([s], filters=filt)
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        assert "document_id=doc_001" in result.evidence_pack.trace.applied_filters


class TestNoProhibitedFields:
    """Evidence pack must not contain answer/reasoning/citation-validation fields."""

    def test_no_answer_in_item(self):
        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        d = result.evidence_pack.items[0].to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "citation_validation" not in d

    def test_no_answer_in_pack(self):
        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        d = result.evidence_pack.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "llm_output" not in d

    def test_no_answer_in_trace(self):
        s = _make_scoring_full()
        resp = _make_response([s])
        result = InMemoryEvidencePackBuilder().build(EvidencePackRequest(retrieval_response=resp))
        d = result.evidence_pack.trace.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "hallucination_score" not in d
