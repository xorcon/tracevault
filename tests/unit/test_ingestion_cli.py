"""Tests for ingestion CLI."""

import json
import subprocess
import sys


class TestIngestCLI:
    """Test ingestion CLI commands."""

    def test_ingest_help(self):
        """ingest --help exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout.lower()

    def test_ingest_single_file(self, tmp_path):
        """Ingest single file exits 0."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "new" in result.stdout.lower()

    def test_ingest_directory(self, tmp_path):
        """Ingest directory exits 0."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")
        file2 = tmp_path / "file2.md"
        file2.write_text("content2", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "new" in result.stdout.lower()

    def test_ingest_missing_path(self, tmp_path):
        """Missing path exits non-zero."""
        missing = tmp_path / "missing"

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", str(missing)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_ingest_json_output(self, tmp_path):
        """--json emits valid JSON."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--json", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "source_path" in data
        assert "status" in data
        assert data["status"] == "new"

    def test_ingest_directory_json(self, tmp_path):
        """Directory --json emits summary."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--json", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "new_count" in data
        assert "total_files" in data
        assert data["new_count"] == 1

    def test_ingest_differential_unchanged(self, tmp_path):
        """Second ingest reports unchanged."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")

        # First ingest
        subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", str(test_file)],
            capture_output=True,
        )

        # Second ingest
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--json", str(test_file)],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["status"] == "unchanged"

    def test_ingest_differential_changed(self, tmp_path):
        """Modified file reports changed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")

        # First ingest
        subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", str(test_file)],
            capture_output=True,
        )

        # Modify
        test_file.write_text("Hello World", encoding="utf-8")

        # Second ingest
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--json", str(test_file)],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["status"] == "changed"

    def test_ingest_unsupported_skipped(self, tmp_path):
        """Unsupported file reports skipped."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF fake")

        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "ingest", "--json", str(test_file)],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["status"] == "skipped"

    def test_ingest_custom_manifest(self, tmp_path):
        """--manifest-path works."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")
        custom_manifest = tmp_path / "custom.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(custom_manifest),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert custom_manifest.exists()
