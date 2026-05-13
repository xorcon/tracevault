"""Tests for evidence pack data models."""

import pytest

from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidenceExclusion,
    EvidenceExclusionReason,
    EvidenceGroup,
    EvidenceItem,
    EvidencePack,
    EvidencePackRequest,
    EvidencePackResponse,
    EvidencePackTrace,
    EvidenceSelectionPolicy,
)
from tracevault.retrieval.models import RetrievalScore, TextRetrievalPolicy


class TestEvidenceExclusionReason:
    def test_reason_codes_exist(self):
        assert EvidenceExclusionReason.MAX_ITEMS_EXCEEDED == "max_items_exceeded"
        assert EvidenceExclusionReason.MAX_RAW_CHARS_EXCEEDED == "max_raw_chars_exceeded"
        assert EvidenceExclusionReason.MAX_CLEANED_CHARS_EXCEEDED == "max_cleaned_chars_exceeded"
        assert EvidenceExclusionReason.MAX_CONTEXT_CHARS_EXCEEDED == "max_context_chars_exceeded"


class TestEvidenceBudget:
    def test_unlimited_by_default(self):
        budget = EvidenceBudget()
        assert budget.is_unlimited() is True

    def test_limited_when_max_items_set(self):
        budget = EvidenceBudget(max_items=5)
        assert budget.is_unlimited() is False

    def test_limited_when_max_raw_chars_set(self):
        budget = EvidenceBudget(max_raw_chars=1000)
        assert budget.is_unlimited() is False

    def test_limited_when_max_cleaned_chars_set(self):
        budget = EvidenceBudget(max_cleaned_chars=1000)
        assert budget.is_unlimited() is False

    def test_limited_when_max_context_chars_set(self):
        budget = EvidenceBudget(max_context_chars=2000)
        assert budget.is_unlimited() is False


class TestEvidenceSelectionPolicy:
    def test_defaults(self):
        policy = EvidenceSelectionPolicy()
        assert policy.order_by == "retrieval_rank"
        assert policy.deduplicate_by == "document_chunk"

    def test_invalid_order_by_raises(self):
        with pytest.raises(ValueError, match="Invalid order_by"):
            EvidenceSelectionPolicy(order_by="invalid")  # type: ignore[arg-type]

    def test_invalid_deduplicate_by_raises(self):
        with pytest.raises(ValueError, match="Invalid deduplicate_by"):
            EvidenceSelectionPolicy(deduplicate_by="invalid")  # type: ignore[arg-type]

    def test_raw_text_hash_dedup(self):
        policy = EvidenceSelectionPolicy(deduplicate_by="raw_text_hash")
        assert policy.deduplicate_by == "raw_text_hash"


class TestContextAssemblyPolicy:
    def test_defaults(self):
        policy = ContextAssemblyPolicy()
        assert policy.include_raw_text is True
        assert policy.include_cleaned_text is True

    def test_raw_only(self):
        policy = ContextAssemblyPolicy(include_cleaned_text=False)
        assert policy.include_raw_text is True
        assert policy.include_cleaned_text is False


class TestEvidenceExclusion:
    def test_exclusion_fields(self):
        exc = EvidenceExclusion(
            document_id="doc_001",
            chunk_id="chunk_001",
            reason="max_items_exceeded",
            budget_field="max_items",
        )
        assert exc.document_id == "doc_001"
        assert exc.chunk_id == "chunk_001"
        assert exc.reason == "max_items_exceeded"
        assert exc.budget_field == "max_items"


class TestEvidenceItem:
    def test_item_preserves_document_id_and_chunk_id(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello world",
            cleaned_text="Hello world",
            raw_text_hash="abc123",
        )
        assert item.document_id == "doc_001"
        assert item.chunk_id == "chunk_001"

    def test_item_preserves_source_path(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/deep/file.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
        )
        assert item.source_path == "docs/deep/file.md"

    def test_item_preserves_raw_text_hash(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="sha256hash",
        )
        assert item.raw_text_hash == "sha256hash"

    def test_item_preserves_cleaned_text_hash(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            cleaned_text_hash="def",
        )
        assert item.cleaned_text_hash == "def"

    def test_item_preserves_retrieval_run_id(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            retrieval_run_id="run_001",
        )
        assert item.retrieval_run_id == "run_001"

    def test_item_preserves_retrieval_source(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            retrieval_source="hybrid",
        )
        assert item.retrieval_source == "hybrid"

    def test_item_preserves_source_retrievers(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            source_retrievers=["keyword", "vector"],
        )
        assert item.source_retrievers == ["keyword", "vector"]

    def test_item_preserves_score_components(self):
        item = EvidenceItem(
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
                vector_score=0.6,
                hybrid_score=0.7,
                alpha=0.5,
                score_policy="hybrid",
            ),
        )
        assert item.score.keyword_score == 0.8
        assert item.score.vector_score == 0.6
        assert item.score.hybrid_score == 0.7
        assert item.score.alpha == 0.5
        assert item.score.score_policy == "hybrid"

    def test_item_preserves_rank(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            rank=3,
        )
        assert item.rank == 3

    def test_item_preserves_raw_text_exactly(self):
        raw = "Original raw text with  \t special   characters"
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text=raw,
            cleaned_text="cleaned",
            raw_text_hash="abc",
        )
        assert item.raw_text == raw

    def test_item_preserves_cleaned_text_exactly(self):
        cleaned = "Cleaned text with  \t special   characters"
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="raw",
            cleaned_text=cleaned,
            raw_text_hash="abc",
        )
        assert item.cleaned_text == cleaned

    def test_item_to_dict(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            rank=1,
            text_policy=TextRetrievalPolicy.dual_context(),
        )
        d = item.to_dict()
        assert d["document_id"] == "doc_001"
        assert d["chunk_id"] == "chunk_001"
        assert d["rank"] == 1
        assert d["text_policy"] == "DUAL_CONTEXT"
        assert "score" in d
        assert "raw_text" in d
        assert "cleaned_text" in d

    def test_no_answer_field(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
        )
        d = item.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "citation_validation" not in d


class TestEvidenceGroup:
    def test_group_to_dict(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
        )
        group = EvidenceGroup(group_name="all", items=[item])
        d = group.to_dict()
        assert d["group_name"] == "all"
        assert len(d["items"]) == 1


class TestEvidencePack:
    def test_pack_to_dict(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
        )
        pack = EvidencePack(
            items=[],
            groups=[],
            context="",
            trace=trace,
        )
        d = pack.to_dict()
        assert "items" in d
        assert "groups" in d
        assert "context" in d
        assert "trace" in d
        assert d["trace"]["pack_id"] == "pack_001"

    def test_no_answer_or_reasoning_fields(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
        )
        pack = EvidencePack(trace=trace)
        d = pack.to_dict()
        assert "answer" not in d
        assert "reasoning" not in d
        assert "llm" not in d
        assert "hallucination" not in d

    def test_evidence_pack_requires_explicit_trace(self):
        """EvidencePack must not allow construction without an explicit trace."""
        with pytest.raises(TypeError, match="missing"):
            EvidencePack()

    def test_evidence_pack_requires_trace_with_items_only(self):
        """Even with items, EvidencePack requires an explicit trace."""
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
        )
        with pytest.raises(TypeError, match="missing"):
            EvidencePack(items=[item])


class TestEvidencePackTraceValidation:
    """EvidencePackTrace must reject degenerate (empty) audit fields."""

    def test_rejects_empty_pack_id(self):
        with pytest.raises(ValueError, match="pack_id"):
            EvidencePackTrace(
                pack_id="",
                retrieval_run_id="run_001",
                query="test",
                query_hash="qhash",
                total_input_results=0,
                total_selected_items=0,
                total_excluded_items=0,
            )

    def test_rejects_empty_retrieval_run_id(self):
        with pytest.raises(ValueError, match="retrieval_run_id"):
            EvidencePackTrace(
                pack_id="pack_001",
                retrieval_run_id="",
                query="test",
                query_hash="qhash",
                total_input_results=0,
                total_selected_items=0,
                total_excluded_items=0,
            )

    def test_rejects_empty_query_hash(self):
        with pytest.raises(ValueError, match="query_hash"):
            EvidencePackTrace(
                pack_id="pack_001",
                retrieval_run_id="run_001",
                query="test",
                query_hash="",
                total_input_results=0,
                total_selected_items=0,
                total_excluded_items=0,
            )

    def test_accepts_valid_trace(self):
        """A trace with all required fields should not raise."""
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
        )
        assert trace.pack_id == "pack_001"
        assert trace.retrieval_run_id == "run_001"
        assert trace.query_hash == "qhash"


class TestEvidencePackRequest:
    def test_request_fields(self):
        from tracevault.retrieval.models import RetrievalResponse

        resp = RetrievalResponse(
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            results=[],
            total_candidates=0,
            alpha=0.5,
            text_policy=TextRetrievalPolicy.dual_context(),
        )
        req = EvidencePackRequest(retrieval_response=resp)
        assert req.retrieval_response is resp
        assert req.selection_policy is None
        assert req.context_policy is None
        assert req.budget is None


class TestEvidencePackResponse:
    def test_response_to_dict(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=0,
            total_selected_items=0,
            total_excluded_items=0,
        )
        pack = EvidencePack(trace=trace)
        resp = EvidencePackResponse(evidence_pack=pack)
        d = resp.to_dict()
        assert "items" in d
        assert "trace" in d


class TestEvidencePackTrace:
    def test_trace_to_dict_preserves_exclusions(self):
        exc = EvidenceExclusion(
            document_id="doc_001",
            chunk_id="chunk_001",
            reason="max_items_exceeded",
            budget_field="max_items",
        )
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=5,
            total_selected_items=3,
            total_excluded_items=2,
            exclusions=[exc],
        )
        d = trace.to_dict()
        assert d["total_input_results"] == 5
        assert d["total_selected_items"] == 3
        assert d["total_excluded_items"] == 2
        assert len(d["exclusions"]) == 1
        assert d["exclusions"][0]["reason"] == "max_items_exceeded"

    def test_trace_to_dict_preserves_policies(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
        )
        d = trace.to_dict()
        assert d["selection_policy"]["order_by"] == "retrieval_rank"
        assert d["selection_policy"]["deduplicate_by"] == "document_chunk"
        assert d["context_policy"]["include_raw_text"] is True
        assert d["context_policy"]["include_cleaned_text"] is True

    def test_trace_to_dict_with_budget(self):
        budget = EvidenceBudget(max_items=5)
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
            budget=budget,
        )
        d = trace.to_dict()
        assert d["budget"]["max_items"] == 5

    def test_trace_to_dict_without_budget(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
        )
        d = trace.to_dict()
        assert d["budget"] is None

    def test_trace_preserves_text_policy(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
            text_policy=TextRetrievalPolicy.raw_only(),
        )
        d = trace.to_dict()
        assert d["text_policy"] == "RAW_ONLY"

    def test_trace_preserves_applied_filters(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
            applied_filters="document_id=doc_001",
        )
        d = trace.to_dict()
        assert d["applied_filters"] == "document_id=doc_001"

    def test_trace_preserves_pack_run_id(self):
        trace = EvidencePackTrace(
            pack_id="pack_001",
            retrieval_run_id="run_001",
            query="test",
            query_hash="qhash",
            total_input_results=1,
            total_selected_items=1,
            total_excluded_items=0,
            pack_run_id="pack_run_001",
        )
        d = trace.to_dict()
        assert d["pack_run_id"] == "pack_run_001"


class TestComputePackId:
    def test_pack_id_is_deterministic(self):
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()
        identities = [("doc_001", "chunk_001")]

        id1 = compute_pack_id("run_001", "qhash", identities, sel, ctx, None)
        id2 = compute_pack_id("run_001", "qhash", identities, sel, ctx, None)
        assert id1 == id2

    def test_pack_id_differs_with_different_input(self):
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()

        id1 = compute_pack_id("run_001", "qhash", [("doc_001", "chunk_001")], sel, ctx, None)
        id2 = compute_pack_id("run_002", "qhash", [("doc_001", "chunk_001")], sel, ctx, None)
        assert id1 != id2

    def test_pack_id_differs_with_different_items(self):
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()

        id1 = compute_pack_id("run_001", "qhash", [("doc_001", "chunk_001")], sel, ctx, None)
        id2 = compute_pack_id("run_001", "qhash", [("doc_001", "chunk_002")], sel, ctx, None)
        assert id1 != id2

    def test_pack_id_is_sha256_hex(self):
        from tracevault.evidence.models import compute_pack_id

        sel = EvidenceSelectionPolicy()
        ctx = ContextAssemblyPolicy()
        pack_id = compute_pack_id("run_001", "qhash", [], sel, ctx, None)
        assert len(pack_id) == 64
        int(pack_id, 16)  # should not raise


class TestTextRetrievalPolicyPreservation:
    def test_item_preserves_text_policy(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            text_policy=TextRetrievalPolicy.raw_only(),
        )
        assert item.text_policy.mode == "RAW_ONLY"

    def test_item_preserves_applied_filters(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            applied_filters=["document_id=doc_001"],
        )
        assert item.applied_filters == ["document_id=doc_001"]

    def test_item_preserves_matched_fields(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            matched_fields=["raw_text", "cleaned_text"],
        )
        assert item.matched_fields == ["raw_text", "cleaned_text"]

    def test_item_preserves_query_hash(self):
        item = EvidenceItem(
            document_id="doc_001",
            chunk_id="chunk_001",
            chunk_index=0,
            source_path="docs/test.md",
            source_type="md",
            raw_text="Hello",
            cleaned_text="Hello",
            raw_text_hash="abc",
            query_hash="qhash123",
        )
        assert item.query_hash == "qhash123"
