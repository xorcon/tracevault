"""Tests for hidden directory exclusion."""

from tracevault.ingestion.manifest import IngestManifest
from tracevault.ingestion.pipeline import ingest_directory


class TestHiddenDirectoryExclusion:
    """Test that hidden directories are excluded from ingestion."""

    def test_hidden_directory_not_ingested(self, tmp_path):
        """Files in .private/ directory are not ingested."""
        # Create hidden directory with file
        hidden_dir = tmp_path / ".private"
        hidden_dir.mkdir()
        hidden_file = hidden_dir / "note.txt"
        hidden_file.write_text("secret", encoding="utf-8")

        # Create visible file
        visible_file = tmp_path / "visible.txt"
        visible_file.write_text("public", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        summary = ingest_directory(tmp_path, manifest)

        assert summary.new_count == 1
        assert summary.skipped_count == 0  # Hidden dir contents skipped entirely

    def test_git_directory_not_ingested(self, tmp_path):
        """Files in .git/ are not ingested."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]", encoding="utf-8")

        visible = tmp_path / "readme.txt"
        visible.write_text("readme", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        summary = ingest_directory(tmp_path, manifest)

        assert summary.new_count == 1

    def test_venv_directory_not_ingested(self, tmp_path):
        """Files in .venv/ are not ingested."""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "script.txt").write_text("script content", encoding="utf-8")

        valid = tmp_path / "code.txt"
        valid.write_text("print(1)", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        summary = ingest_directory(tmp_path, manifest)

        assert summary.new_count == 1

    def test_nested_hidden_directory_not_ingested(self, tmp_path):
        """Nested hidden directories are excluded."""
        # Valid structure
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.txt").write_text("readme", encoding="utf-8")

        # Hidden nested
        hidden_nested = docs / ".hidden"
        hidden_nested.mkdir()
        (hidden_nested / "secret.txt").write_text("secret", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        summary = ingest_directory(tmp_path, manifest)

        assert summary.new_count == 1

    def test_runtime_ignore_list_still_works(self, tmp_path):
        """Explicit runtime dirs (data/, storage/) still ignored."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "file.txt").write_text("data", encoding="utf-8")

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        (storage_dir / "file.txt").write_text("storage", encoding="utf-8")

        valid = tmp_path / "valid.txt"
        valid.write_text("valid", encoding="utf-8")

        manifest_path = tmp_path / ".tracevault" / "manifest.json"
        manifest = IngestManifest(manifest_path)

        summary = ingest_directory(tmp_path, manifest)

        assert summary.new_count == 1
        assert summary.skipped_count == 0  # Runtime dirs skipped entirely
