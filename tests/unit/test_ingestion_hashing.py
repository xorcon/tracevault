"""Tests for ingestion hashing."""


from tracevault.ingestion.hashing import (
    compute_content_hash,
    compute_file_hash,
    verify_hash,
)


class TestHashing:
    """Test SHA-256 hashing utilities."""

    def test_same_content_same_hash(self):
        """Same content produces identical hash."""
        content = "Hello, World!"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_different_content_different_hash(self):
        """Different content produces different hash."""
        hash1 = compute_content_hash("Hello")
        hash2 = compute_content_hash("World")
        assert hash1 != hash2

    def test_case_sensitive(self):
        """Hash is case sensitive."""
        hash1 = compute_content_hash("Hello")
        hash2 = compute_content_hash("hello")
        assert hash1 != hash2

    def test_bytes_input(self):
        """Accepts bytes input."""
        content = b"Hello"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash("Hello")
        assert hash1 == hash2

    def test_empty_string(self):
        """Empty string produces valid hash."""
        hash1 = compute_content_hash("")
        assert len(hash1) == 64

    def test_unicode_content(self):
        """Handles unicode content."""
        content = "こんにちは世界"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_verify_hash_success(self):
        """verify_hash returns True for matching content."""
        content = "test"
        expected = compute_content_hash(content)
        assert verify_hash(content, expected) is True

    def test_verify_hash_failure(self):
        """verify_hash returns False for mismatched content."""
        content = "test"
        wrong_hash = "0" * 64
        assert verify_hash(content, wrong_hash) is False

    def test_file_hash_consistency(self, tmp_path):
        """File hash matches content hash."""
        test_file = tmp_path / "test.txt"
        content = "file content"
        test_file.write_text(content, encoding="utf-8")

        file_hash = compute_file_hash(test_file)
        content_hash = compute_content_hash(content)
        assert file_hash == content_hash

    def test_file_hash_different_content(self, tmp_path):
        """Different file contents produce different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1", encoding="utf-8")
        file2.write_text("content2", encoding="utf-8")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)
        assert hash1 != hash2
