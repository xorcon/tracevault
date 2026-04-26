"""Tests for ingest manifest."""

from pathlib import Path

from tracevault.ingestion.manifest import IngestManifest


class TestManifest:
    """Test manifest management."""

    def test_new_file_detected(self, tmp_path):
        """New file returns 'new' status."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        status = manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )
        assert status == "new"

    def test_unchanged_file_detected(self, tmp_path):
        """Same hash returns 'unchanged' status."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        # First ingest
        manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )

        # Second ingest with same hash
        status = manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-03T00:00:00Z",
        )
        assert status == "unchanged"

    def test_changed_file_detected(self, tmp_path):
        """Different hash returns 'changed' status."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        # First ingest
        manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )

        # Second ingest with different hash
        status = manifest.update_entry(
            source_path="test.txt",
            content_hash="def456",
            size_bytes=200,
            modified_time="2024-01-02T00:00:00Z",
            ingested_at="2024-01-03T00:00:00Z",
        )
        assert status == "changed"

    def test_save_and_reload(self, tmp_path):
        """Manifest persists across saves."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )
        manifest.save()

        # Reload
        manifest2 = IngestManifest(manifest_path)
        entry = manifest2.get_entry("test.txt")
        assert entry is not None
        assert entry.content_hash == "abc123"
        assert entry.size_bytes == 100

    def test_normalize_path(self, tmp_path):
        """Path normalization works."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        # Test relative path
        path = Path("docs/test.md")
        normalized = manifest.normalize_path(path)
        assert "test.md" in normalized

    def test_remove_entry(self, tmp_path):
        """Can remove entries."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        manifest.update_entry(
            source_path="test.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )

        removed = manifest.remove_entry("test.txt")
        assert removed is True
        assert manifest.get_entry("test.txt") is None

    def test_clear(self, tmp_path):
        """Can clear all entries."""
        manifest_path = tmp_path / "manifest.json"
        manifest = IngestManifest(manifest_path)

        manifest.update_entry(
            source_path="test1.txt",
            content_hash="abc123",
            size_bytes=100,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )
        manifest.update_entry(
            source_path="test2.txt",
            content_hash="def456",
            size_bytes=200,
            modified_time="2024-01-01T00:00:00Z",
            ingested_at="2024-01-02T00:00:00Z",
        )

        manifest.clear()
        assert len(manifest.get_all_entries()) == 0

    def test_corrupted_manifest_recovery(self, tmp_path):
        """Handles corrupted manifest gracefully."""
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("not valid json", encoding="utf-8")

        # Should not crash, start with empty entries
        manifest = IngestManifest(manifest_path)
        assert len(manifest.get_all_entries()) == 0
