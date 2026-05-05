"""Tests for InMemoryEvidencePackBuilder."""

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidenceExclusionReason,
    EvidencePackRequest,
    EvidenceSelectionPolicy,
)
from tracevault.retrieval.audit import build_response, rank_candidates
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)


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
    score=None,
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
        score=score or RetrievalScore(),
        metadata=metadata or {},
    )


def _make_response(results_list, query="test", retrieval_run_id="run_001", filters=None):
    """Build a RetrievalResponse from a list of ScoringCandidate."""
    results = rank_candidates(
        candidates=results_list,
        retrieval_run_id=retrieval_run_id,
        query_hash="qhash",
        top_k=10,
        filters=filters,
    )
    return build_response(
        results=results,
        query=query,
        retrieval_run_id=retrieval_run_id,
        total_candidates=len(results_list),
        alpha=0.5,
        text_policy=TextRetrievalPolicy.dual_context(),
        filters=filters,
    )


def _make_scoring(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
    keyword_score=0.8,
    vector_score=0.6,
    matched_fields=None,
    retrieval_source="hybrid",
    source_retrievers=None,
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
        matched_fields=matched_fields or ["raw_text"],
        retrieval_source=retrieval_source,
        source_retrievers=source_retrievers or ["keyword", "vector"],
    )


class TestBasicEvidencePackBuild:
    def test_builds_pack_from_response(self):
        scorings = [_make_scoring(keyword_score=0.8)]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        req = EvidencePackRequest(retrieval_response=resp)
        result = builder.build(req)

        assert len(result.evidence_pack.items) == 1
        assert result.evidence_pack.items[0].document_id == "doc_001"

    def test_preserves_document_id_and_chunk_id(self):
        scorings = [_make_scoring(document_id="doc_abc", chunk_id="chunk_abc_5")]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        item = result.evidence_pack.items[0]
        assert item.document_id == "doc_abc"
        assert item.chunk_id == "chunk_abc_5"

    def test_preserves_source_path(self):
        c = _make_candidate(source_path="docs/deep/file.md", raw_text="Hello world", cleaned_text="Hello world")
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].source_path == "docs/deep/file.md"

    def test_preserves_raw_text_hash(self):
        c = _make_candidate(raw_text_hash="sha256hash", raw_text="Hello world", cleaned_text="Hello world")
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].raw_text_hash == "sha256hash"

    def test_preserves_cleaned_text_hash(self):
        c = _make_candidate(
            raw_text="Hello world",
            cleaned_text="Hello world",
            raw_text_hash="abc",
            cleaned_text_hash="def",
        )
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].cleaned_text_hash == "def"

    def test_preserves_retrieval_run_id(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings, retrieval_run_id="run_custom")
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].retrieval_run_id == "run_custom"

    def test_preserves_retrieval_source(self):
        s = _make_scoring(retrieval_source="keyword", source_retrievers=["keyword"])
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].retrieval_source == "keyword"

    def test_preserves_source_retrievers(self):
        s = _make_scoring(source_retrievers=["keyword", "custom_vector"])
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].source_retrievers == ["keyword", "custom_vector"]

    def test_preserves_score_components(self):
        c = _make_candidate(
            raw_text="Hello world",
            cleaned_text="Hello world",
            score=RetrievalScore(
                keyword_score=0.8,
                vector_score=0.6,
                hybrid_score=0.7,
                alpha=0.6,
                score_policy="hybrid",
            ),
        )
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(
                keyword_score=0.8,
                vector_score=0.6,
                hybrid_score=0.7,
                alpha=0.6,
                score_policy="hybrid",
            ),
            matched_fields=["raw_text"],
            retrieval_source="hybrid",
            source_retrievers=["keyword", "vector"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        item = result.evidence_pack.items[0]
        assert item.score.keyword_score == 0.8
        assert item.score.vector_score == 0.6
        assert item.score.hybrid_score == 0.7
        assert item.score.alpha == 0.6
        assert item.score.score_policy == "hybrid"

    def test_preserves_rank(self):
        scorings = [
            _make_scoring(chunk_id="chunk_001", keyword_score=0.9),
            _make_scoring(chunk_id="chunk_002", keyword_score=0.7),
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].rank == 1
        assert result.evidence_pack.items[1].rank == 2

    def test_preserves_raw_text_exactly(self):
        raw = "Original raw text with  \t special   characters"
        c = _make_candidate(raw_text=raw, cleaned_text=raw)
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].raw_text == raw

    def test_preserves_cleaned_text_exactly(self):
        cleaned = "Cleaned text with  \t special   characters"
        c = _make_candidate(raw_text="raw", cleaned_text=cleaned)
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["cleaned_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].cleaned_text == cleaned

    def test_preserves_text_policy(self):
        scorings = [_make_scoring()]
        results = rank_candidates(
            candidates=scorings,
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=10,
            filters=None,
        )
        resp = build_response(
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

        assert result.evidence_pack.items[0].text_policy.mode == "RAW_ONLY"

    def test_preserves_applied_filters(self):
        s = _make_scoring()
        filt = MetadataFilter(document_id="doc_001")
        resp = _make_response([s], filters=filt)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert "document_id=doc_001" in result.evidence_pack.items[0].applied_filters

    def test_preserves_query_hash(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].query_hash == "qhash"

    def test_preserves_matched_fields(self):
        s = _make_scoring(matched_fields=["raw_text", "cleaned_text"])
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.items[0].matched_fields == ["raw_text", "cleaned_text"]


class TestDeduplication:
    def test_deduplicates_by_document_chunk(self):
        """Same (document_id, chunk_id) should only appear once."""
        s1 = _make_scoring(chunk_id="chunk_001", keyword_score=0.9)
        s2 = _make_scoring(chunk_id="chunk_001", keyword_score=0.7)  # duplicate
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        chunk_ids = [i.chunk_id for i in result.evidence_pack.items]
        assert chunk_ids.count("chunk_001") == 1

    def test_deduplicates_by_raw_text_hash(self):
        """Same raw_text_hash should only appear once with raw_text_hash dedup."""
        c1 = _make_candidate(chunk_id="chunk_001", raw_text_hash="same_hash", raw_text="Hello", cleaned_text="Hello")
        c2 = _make_candidate(chunk_id="chunk_002", raw_text_hash="same_hash", raw_text="Hello", cleaned_text="Hello")
        s1 = ScoringCandidate(
            candidate=c1,
            score=RetrievalScore(keyword_score=0.9, hybrid_score=0.9, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        s2 = ScoringCandidate(
            candidate=c2,
            score=RetrievalScore(keyword_score=0.7, hybrid_score=0.7, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        sel = EvidenceSelectionPolicy(deduplicate_by="raw_text_hash")
        result = builder.build(EvidencePackRequest(retrieval_response=resp, selection_policy=sel))

        assert len(result.evidence_pack.items) == 1

    def test_keeps_first_by_rank_for_document_chunk_dedup(self):
        """When dedup by document_chunk, the first by rank is kept."""
        s1 = _make_scoring(chunk_id="chunk_001", keyword_score=0.9)
        s2 = _make_scoring(chunk_id="chunk_001", keyword_score=0.7)
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert len(result.evidence_pack.items) == 1
        assert result.evidence_pack.items[0].rank == 1


class TestOrdering:
    def test_ordering_is_deterministic_by_rank(self):
        scorings = [
            _make_scoring(chunk_id="chunk_003", keyword_score=0.5),
            _make_scoring(chunk_id="chunk_001", keyword_score=0.9),
            _make_scoring(chunk_id="chunk_002", keyword_score=0.7),
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        ranks = [i.rank for i in result.evidence_pack.items]
        assert ranks == sorted(ranks)


class TestBudgetExclusion:
    def test_max_items_exclusion(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=3)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        assert len(result.evidence_pack.items) == 3
        assert result.evidence_pack.trace.total_excluded_items == 2
        assert result.evidence_pack.trace.exclusions[0].reason == EvidenceExclusionReason.MAX_ITEMS_EXCEEDED

    def test_max_raw_chars_exclusion(self):
        c1 = _make_candidate(chunk_id="chunk_001", raw_text="A" * 100, cleaned_text="A" * 100)
        c2 = _make_candidate(chunk_id="chunk_002", raw_text="B" * 100, cleaned_text="B" * 100)
        s1 = ScoringCandidate(
            candidate=c1,
            score=RetrievalScore(keyword_score=0.9, hybrid_score=0.9, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        s2 = ScoringCandidate(
            candidate=c2,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_raw_chars=150)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        assert len(result.evidence_pack.items) == 1
        assert result.evidence_pack.trace.exclusions[0].reason == EvidenceExclusionReason.MAX_RAW_CHARS_EXCEEDED

    def test_max_cleaned_chars_exclusion(self):
        c1 = _make_candidate(chunk_id="chunk_001", raw_text="A", cleaned_text="A" * 100)
        c2 = _make_candidate(chunk_id="chunk_002", raw_text="B", cleaned_text="B" * 100)
        s1 = ScoringCandidate(
            candidate=c1,
            score=RetrievalScore(keyword_score=0.9, hybrid_score=0.9, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        s2 = ScoringCandidate(
            candidate=c2,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_cleaned_chars=150)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        assert len(result.evidence_pack.items) == 1
        assert result.evidence_pack.trace.exclusions[0].reason == EvidenceExclusionReason.MAX_CLEANED_CHARS_EXCEEDED

    def test_max_context_chars_exclusion(self):
        c1 = _make_candidate(chunk_id="chunk_001", raw_text="A" * 50, cleaned_text="A" * 50)
        c2 = _make_candidate(chunk_id="chunk_002", raw_text="B" * 50, cleaned_text="B" * 50)
        s1 = ScoringCandidate(
            candidate=c1,
            score=RetrievalScore(keyword_score=0.9, hybrid_score=0.9, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        s2 = ScoringCandidate(
            candidate=c2,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s1, s2])
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_context_chars=120)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        assert len(result.evidence_pack.items) == 1
        assert result.evidence_pack.trace.exclusions[0].reason == EvidenceExclusionReason.MAX_CONTEXT_CHARS_EXCEEDED

    def test_exclusion_includes_mechanical_reason(self):
        scorings = [
            _make_scoring(chunk_id=f"chunk_00{i}", keyword_score=0.9 - i * 0.1)
            for i in range(3)
        ]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        budget = EvidenceBudget(max_items=1)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, budget=budget))

        for exc in result.evidence_pack.trace.exclusions:
            assert exc.reason in (
                EvidenceExclusionReason.MAX_ITEMS_EXCEEDED,
                EvidenceExclusionReason.MAX_RAW_CHARS_EXCEEDED,
                EvidenceExclusionReason.MAX_CLEANED_CHARS_EXCEEDED,
                EvidenceExclusionReason.MAX_CONTEXT_CHARS_EXCEEDED,
            )

    def test_no_answer_field_in_pack(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        d = result.evidence_pack.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "citation_validation" not in d


class TestContextAssembly:
    def test_context_includes_evidence_blocks(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert "[EVIDENCE 1]" in result.evidence_pack.context
        assert "document_id:" in result.evidence_pack.context
        assert "chunk_id:" in result.evidence_pack.context
        assert "RAW_TEXT:" in result.evidence_pack.context
        assert "CLEANED_TEXT:" in result.evidence_pack.context

    def test_context_raw_only(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        ctx = ContextAssemblyPolicy(include_cleaned_text=False)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, context_policy=ctx))

        assert "RAW_TEXT:" in result.evidence_pack.context
        assert "CLEANED_TEXT:" not in result.evidence_pack.context

    def test_context_cleaned_only(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        ctx = ContextAssemblyPolicy(include_raw_text=False)
        result = builder.build(EvidencePackRequest(retrieval_response=resp, context_policy=ctx))

        assert "RAW_TEXT:" not in result.evidence_pack.context
        assert "CLEANED_TEXT:" in result.evidence_pack.context

    def test_context_includes_traceability_fields(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        ctx = result.evidence_pack.context
        assert "source_path:" in ctx
        assert "retrieval_rank:" in ctx
        assert "retrieval_source:" in ctx
        assert "source_retrievers:" in ctx
        assert "raw_text_hash:" in ctx


class TestEmptyResponse:
    def test_empty_response_produces_empty_pack(self):
        resp = _make_response([])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert len(result.evidence_pack.items) == 0
        assert result.evidence_pack.context == ""
        assert result.evidence_pack.trace.total_input_results == 0
        assert result.evidence_pack.trace.total_selected_items == 0


class TestPackTrace:
    def test_trace_has_pack_id(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.trace.pack_id != ""
        assert len(result.evidence_pack.trace.pack_id) == 64

    def test_trace_preserves_retrieval_run_id(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings, retrieval_run_id="run_custom")
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.trace.retrieval_run_id == "run_custom"

    def test_trace_preserves_query(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings, query="my query")
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert result.evidence_pack.trace.query == "my query"

    def test_trace_preserves_text_policy(self):
        results = rank_candidates(
            candidates=[_make_scoring()],
            retrieval_run_id="run_001",
            query_hash="qhash",
            top_k=10,
            filters=None,
        )
        resp = build_response(
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

        assert result.evidence_pack.trace.text_policy.mode == "RAW_ONLY"

    def test_trace_preserves_applied_filters(self):
        s = _make_scoring()
        filt = MetadataFilter(document_id="doc_001")
        resp = _make_response([s], filters=filt)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        assert "document_id=doc_001" in result.evidence_pack.trace.applied_filters

    def test_trace_preserves_pack_run_id(self):
        scorings = [_make_scoring()]
        resp = _make_response(scorings)
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(
            EvidencePackRequest(retrieval_response=resp, pack_run_id="pack_run_001")
        )

        assert result.evidence_pack.trace.pack_run_id == "pack_run_001"


class TestCandidateMetadataPreservation:
    def test_candidate_metadata_copied_not_shared(self):
        c = _make_candidate(metadata={"env": "prod"}, raw_text="Hello world", cleaned_text="Hello world")
        s = ScoringCandidate(
            candidate=c,
            score=RetrievalScore(keyword_score=0.8, hybrid_score=0.8, score_policy="keyword"),
            matched_fields=["raw_text"],
            retrieval_source="keyword",
            source_retrievers=["keyword"],
        )
        resp = _make_response([s])
        builder = InMemoryEvidencePackBuilder()
        result = builder.build(EvidencePackRequest(retrieval_response=resp))

        item = result.evidence_pack.items[0]
        assert item.candidate_metadata == {"env": "prod"}
        # Mutating the copy should not affect the original
        item.candidate_metadata["new_key"] = "new_value"
        assert "new_key" not in c.metadata
