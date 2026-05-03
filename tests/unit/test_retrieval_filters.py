"""Tests for retrieval metadata filtering."""

from tracevault.retrieval.filters import (
    apply_filters,
    describe_filters,
    filter_by_document_id,
    filter_by_metadata,
    filter_by_source_path,
    filter_by_source_type,
)
from tracevault.retrieval.models import CandidateEvidence, MetadataFilter


def _make_candidate(
    document_id="doc_001",
    chunk_id="chunk_doc_001_0",
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
        chunk_index=0,
        source_path=source_path,
        source_type=source_type,
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        raw_text_hash=raw_text_hash,
        metadata=metadata or {},
    )


class TestApplyFilters:
    def test_no_filter_returns_all(self):
        candidates = [_make_candidate(document_id="doc_001"), _make_candidate(document_id="doc_002")]
        result = apply_filters(candidates, None)
        assert len(result) == 2

    def test_empty_filter_returns_all(self):
        candidates = [_make_candidate(document_id="doc_001"), _make_candidate(document_id="doc_002")]
        result = apply_filters(candidates, MetadataFilter())
        assert len(result) == 2

    def test_filter_by_document_id(self):
        candidates = [
            _make_candidate(document_id="doc_001"),
            _make_candidate(document_id="doc_002"),
        ]
        f = MetadataFilter(document_id="doc_001")
        result = apply_filters(candidates, f)
        assert len(result) == 1
        assert result[0].document_id == "doc_001"

    def test_filter_no_match_returns_empty(self):
        candidates = [_make_candidate(document_id="doc_001")]
        f = MetadataFilter(document_id="doc_999")
        result = apply_filters(candidates, f)
        assert len(result) == 0

    def test_filter_by_source_path(self):
        candidates = [
            _make_candidate(source_path="docs/a.md"),
            _make_candidate(source_path="docs/b.md"),
        ]
        f = MetadataFilter(source_path="docs/a.md")
        result = apply_filters(candidates, f)
        assert len(result) == 1
        assert result[0].source_path == "docs/a.md"

    def test_filter_by_source_type(self):
        candidates = [
            _make_candidate(source_type="md"),
            _make_candidate(source_type="txt"),
        ]
        f = MetadataFilter(source_type="md")
        result = apply_filters(candidates, f)
        assert len(result) == 1
        assert result[0].source_type == "md"

    def test_filter_by_key_value(self):
        candidates = [
            _make_candidate(metadata={"env": "prod"}),
            _make_candidate(metadata={"env": "dev"}),
        ]
        f = MetadataFilter(key_value={"env": "prod"})
        result = apply_filters(candidates, f)
        assert len(result) == 1
        assert result[0].metadata["env"] == "prod"

    def test_combined_filter_all_match(self):
        candidates = [
            _make_candidate(
                document_id="doc_001",
                source_path="docs/a.md",
                source_type="md",
                metadata={"env": "prod"},
            ),
            _make_candidate(
                document_id="doc_002",
                source_path="docs/b.md",
                source_type="txt",
                metadata={"env": "dev"},
            ),
        ]
        f = MetadataFilter(
            document_id="doc_001",
            source_path="docs/a.md",
            source_type="md",
            key_value={"env": "prod"},
        )
        result = apply_filters(candidates, f)
        assert len(result) == 1

    def test_combined_filter_partial_match(self):
        candidates = [_make_candidate(document_id="doc_001", source_type="md")]
        f = MetadataFilter(document_id="doc_001", source_type="txt")
        result = apply_filters(candidates, f)
        assert len(result) == 0


class TestFilterByDocumentId:
    def test_returns_matching(self):
        candidates = [
            _make_candidate(document_id="doc_001"),
            _make_candidate(document_id="doc_002"),
        ]
        result = filter_by_document_id(candidates, "doc_001")
        assert len(result) == 1
        assert result[0].document_id == "doc_001"

    def test_returns_empty_on_no_match(self):
        candidates = [_make_candidate(document_id="doc_001")]
        result = filter_by_document_id(candidates, "doc_999")
        assert len(result) == 0


class TestFilterBySourcePath:
    def test_returns_matching(self):
        candidates = [
            _make_candidate(source_path="docs/a.md"),
            _make_candidate(source_path="docs/b.md"),
        ]
        result = filter_by_source_path(candidates, "docs/a.md")
        assert len(result) == 1

    def test_returns_empty_on_no_match(self):
        candidates = [_make_candidate(source_path="docs/a.md")]
        result = filter_by_source_path(candidates, "docs/missing.md")
        assert len(result) == 0


class TestFilterBySourceType:
    def test_returns_matching(self):
        candidates = [
            _make_candidate(source_type="md"),
            _make_candidate(source_type="txt"),
        ]
        result = filter_by_source_type(candidates, "md")
        assert len(result) == 1

    def test_returns_empty_on_no_match(self):
        candidates = [_make_candidate(source_type="md")]
        result = filter_by_source_type(candidates, "pdf")
        assert len(result) == 0


class TestFilterByMetadata:
    def test_returns_matching(self):
        candidates = [
            _make_candidate(metadata={"env": "prod"}),
            _make_candidate(metadata={"env": "dev"}),
        ]
        result = filter_by_metadata(candidates, "env", "prod")
        assert len(result) == 1

    def test_returns_empty_on_no_match(self):
        candidates = [_make_candidate(metadata={"env": "prod"})]
        result = filter_by_metadata(candidates, "env", "staging")
        assert len(result) == 0

    def test_returns_empty_on_missing_key(self):
        candidates = [_make_candidate(metadata={})]
        result = filter_by_metadata(candidates, "env", "prod")
        assert len(result) == 0


class TestDescribeFilters:
    def test_none_returns_empty(self):
        assert describe_filters(None) == ""

    def test_empty_returns_empty(self):
        assert describe_filters(MetadataFilter()) == ""

    def test_single_filter(self):
        f = MetadataFilter(document_id="doc_001")
        assert describe_filters(f) == "document_id=doc_001"

    def test_multiple_filters(self):
        f = MetadataFilter(
            document_id="doc_001",
            source_path="docs/a.md",
            source_type="md",
        )
        desc = describe_filters(f)
        assert "document_id=doc_001" in desc
        assert "source_path=docs/a.md" in desc
        assert "source_type=md" in desc

    def test_key_value_in_description(self):
        f = MetadataFilter(key_value={"env": "prod"})
        assert describe_filters(f) == "env=prod"
