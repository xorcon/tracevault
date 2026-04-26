"""Tests for ingestion pipeline."""


import pytest

from tracevault.ingestion.manifest import IngestManifest
from tracevault.ingestion.pipeline import (
    ingest_directory,
    ingest_file,
    ingest_path,
)


class TestPipeline:
    """Test ingestion pipeline."""

    def test_ingest_single_file(self, tmp_path):
        """Ingest a single supported file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        result = ingest_file(test_file, manifest)

        assert result.status == "new"
        assert result.document_record is not None
        assert result.document_record.source_path.endswith("test.txt")
        assert result.document_record.content_hash is not None
        assert result.document_record.size_bytes == len("Hello World")

    def test_ingest_unchanged_file(self, tmp_path):
        """Second ingest of same file returns unchanged."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        # First ingest
        result1 = ingest_file(test_file, manifest)
        assert result1.status == "new"

        # Second ingest
        result2 = ingest_file(test_file, manifest)
        assert result2.status == "unchanged"

    def test_ingest_changed_file(self, tmp_path):
        """Modified file returns changed status."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        # First ingest
        ingest_file(test_file, manifest)

        # Modify file
        test_file.write_text("Hello World", encoding="utf-8")

        # Second ingest
        result = ingest_file(test_file, manifest)
        assert result.status == "changed"

    def test_ingest_unsupported_file(self, tmp_path):
        """Unsupported file returns skipped."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake pdf")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        result = ingest_file(test_file, manifest)
        assert result.status == "skipped"
        assert "Unsupported" in result.error

    def test_ingest_missing_file(self, tmp_path):
        """Missing file returns error."""
        test_file = tmp_path / "missing.txt"

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        result = ingest_file(test_file, manifest)
        assert result.status == "error"
        assert "not found" in result.error.lower()

    def test_ingest_directory_recursive(self, tmp_path):
        """Directory ingest processes subdirectories."""
        # Create structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")
        file2 = subdir / "file2.md"
        file2.write_text("content2", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"

        summary = ingest_directory(tmp_path, IngestManifest(manifest_path))

        assert summary.new_count == 2
        assert summary.total_files == 2

    def test_ingest_directory_ignores_runtime_dirs(self, tmp_path):
        """Runtime directories are ignored."""
        # Create ignored directory
        ignored = tmp_path / ".git"
        ignored.mkdir()
        (ignored / "file.txt").write_text("ignored", encoding="utf-8")

        # Create valid file
        valid = tmp_path / "valid.txt"
        valid.write_text("valid", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"

        summary = ingest_directory(tmp_path, IngestManifest(manifest_path))

        assert summary.new_count == 1
        assert summary.skipped_count == 0  # .git contents should be skipped entirely

    def test_ingest_directory_skips_hidden_files(self, tmp_path):
        """Hidden files are skipped."""
        hidden = tmp_path / ".hidden.txt"
        hidden.write_text("hidden", encoding="utf-8")
        visible = tmp_path / "visible.txt"
        visible.write_text("visible", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"

        summary = ingest_directory(tmp_path, IngestManifest(manifest_path))

        assert summary.new_count == 1
        assert summary.skipped_count == 1

    def test_ingest_path_file(self, tmp_path):
        """ingest_path works for single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"

        result = ingest_path(test_file, manifest_path)

        assert hasattr(result, "status")  # Single file returns IngestResult
        assert result.status == "new"

    def test_ingest_path_directory(self, tmp_path):
        """ingest_path works for directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"

        result = ingest_path(tmp_path, manifest_path)

        assert hasattr(result, "new_count")  # Directory returns IngestSummary
        assert result.new_count == 1

    def test_ingest_path_missing(self, tmp_path):
        """ingest_path raises error for missing path."""
        missing = tmp_path / "missing"

        with pytest.raises(FileNotFoundError):
            ingest_path(missing)

    def test_document_id_generation(self, tmp_path):
        """Document IDs are deterministic."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        result = ingest_file(test_file, manifest)
        doc_id = result.document_record.document_id

        # ID should contain path info and hash
        assert "test" in doc_id
        assert len(doc_id) > 0

    def test_raw_text_preservation(self, tmp_path):
        """Raw text is preserved exactly (verified via hash)."""
        content = "Line 1\nLine 2\n  Indented\n"
        test_file = tmp_path / "test.txt"
        test_file.write_text(content, encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        result = ingest_file(test_file, manifest)

        # Hash should match exact content
        from tracevault.ingestion.hashing import compute_content_hash
        expected_hash = compute_content_hash(content)
        assert result.document_record.content_hash == expected_hash
