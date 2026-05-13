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
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
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
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "new" in result.stdout.lower()

    def test_ingest_missing_path(self, tmp_path):
        """Missing path exits non-zero."""
        missing = tmp_path / "missing"
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(missing),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_ingest_json_output(self, tmp_path):
        """--json emits valid JSON."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
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
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(tmp_path),
            ],
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
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # First ingest
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
        )

        # Second ingest
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["status"] == "unchanged"

    def test_ingest_differential_changed(self, tmp_path):
        """Modified file reports changed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # First ingest
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
        )

        # Modify
        test_file.write_text("Hello World", encoding="utf-8")

        # Second ingest
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["status"] == "changed"

    def test_ingest_unsupported_skipped(self, tmp_path):
        """Unsupported file reports skipped."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF fake")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
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

    def test_ingest_single_file_error_exits_1(self, tmp_path):
        """Single file with error status exits 1."""
        test_file = tmp_path / "error.txt"
        test_file.write_text("Hello", encoding="utf-8")
        test_file.chmod(0o000)
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tracevault",
                    "ingest",
                    "--manifest-path",
                    str(manifest_path),
                    str(test_file),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
        finally:
            test_file.chmod(0o644)

    def test_ingest_directory_with_errors_exits_1(self, tmp_path):
        """Directory ingest with error_count > 0 exits 1."""
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("valid", encoding="utf-8")

        error_file = tmp_path / "error.txt"
        error_file.write_text("error", encoding="utf-8")
        error_file.chmod(0o000)
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tracevault",
                    "ingest",
                    "--manifest-path",
                    str(manifest_path),
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "error" in result.stdout.lower() or "error" in result.stderr.lower()
        finally:
            error_file.chmod(0o644)

    def test_ingest_directory_error_json_valid(self, tmp_path):
        """Directory with errors still produces valid JSON with --json."""
        error_file = tmp_path / "error.txt"
        error_file.write_text("error", encoding="utf-8")
        error_file.chmod(0o000)
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tracevault",
                    "ingest",
                    "--json",
                    "--manifest-path",
                    str(manifest_path),
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
            )
            data = json.loads(result.stdout)
            assert "error_count" in data
            assert data["error_count"] > 0
            assert result.returncode == 1
        finally:
            error_file.chmod(0o644)

    def test_ingest_unsupported_exits_0(self, tmp_path):
        """Unsupported file (skipped) exits 0."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF fake")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_ingest_corrupted_manifest_exits_1(self, tmp_path):
        """Corrupted manifest exits 1 with clear error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("not valid json", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "corrupt" in result.stderr.lower() or "corrupt" in result.stdout.lower()

    def test_ingest_corrupted_manifest_json(self, tmp_path):
        """Corrupted manifest with --json outputs valid JSON error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-8")
        manifest_path = tmp_path / ".tracevault" / "ingest-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("not valid json", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tracevault",
                "ingest",
                "--json",
                "--manifest-path",
                str(manifest_path),
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data
        assert "corrupt" in data["error"].lower()
