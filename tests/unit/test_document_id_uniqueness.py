"""Tests for document_id collision resistance."""

from tracevault.ingestion.models import DocumentRecord


class TestDocumentIdUniqueness:
    """Test document_id generation prevents collisions."""

    def test_same_basename_different_directories_different_ids(self):
        """Files with same basename in different dirs have different document_ids."""
        content_hash = "abc123def456789012345678901234567890abcdef"

        id1 = DocumentRecord.generate_document_id("a/test.txt", content_hash)
        id2 = DocumentRecord.generate_document_id("b/test.txt", content_hash)

        assert id1 != id2
        assert id1.startswith("doc_")
        assert id2.startswith("doc_")

    def test_same_path_same_content_same_id(self):
        """Same path and content produce identical document_id."""
        content_hash = "abc123def456789012345678901234567890abcdef"

        id1 = DocumentRecord.generate_document_id("docs/test.txt", content_hash)
        id2 = DocumentRecord.generate_document_id("docs/test.txt", content_hash)

        assert id1 == id2

    def test_same_path_different_content_different_id(self):
        """Same path with different content produce different document_id."""
        hash1 = "abc123def456789012345678901234567890abcdef"
        hash2 = "def456abc789012345678901234567890123456789"

        id1 = DocumentRecord.generate_document_id("docs/test.txt", hash1)
        id2 = DocumentRecord.generate_document_id("docs/test.txt", hash2)

        assert id1 != id2

    def test_different_path_same_content_different_id(self):
        """Different paths with same content have different document_ids."""
        content_hash = "abc123def456789012345678901234567890abcdef"

        id1 = DocumentRecord.generate_document_id("docs/test.txt", content_hash)
        id2 = DocumentRecord.generate_document_id("src/test.txt", content_hash)

        assert id1 != id2

    def test_document_id_format(self):
        """document_id follows doc_<path_hash_12>_<content_hash_12> format."""
        content_hash = "abc123def456789012345678901234567890abcdef"
        doc_id = DocumentRecord.generate_document_id("docs/test.txt", content_hash)

        # Format: doc_XXXXXXXXXXXX_YYYYYYYYYYYY (12 hex chars each)
        assert doc_id.startswith("doc_")
        parts = doc_id.split("_")
        assert len(parts) == 3  # doc, path_hash, content_hash
        assert len(parts[1]) == 12  # path hash
        assert len(parts[2]) == 12  # content hash
        assert parts[2] == "abc123def456"  # first 12 of content_hash

    def test_deep_nested_paths_different_ids(self):
        """Deep nested paths with same basename are distinct."""
        content_hash = "abc123def456789012345678901234567890abcdef"

        id1 = DocumentRecord.generate_document_id("a/b/c/d/test.txt", content_hash)
        id2 = DocumentRecord.generate_document_id("x/y/z/test.txt", content_hash)

        assert id1 != id2
