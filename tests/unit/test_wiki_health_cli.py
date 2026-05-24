"""Tests for wiki-health CLI command."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path


def _valid_note(note_id: str = "note_001") -> str:
    return textwrap.dedent(f'''\
        ---
        note_id: "{note_id}"
        note_type: "compiled_knowledge_wiki_note"
        status: "proposal"
        generated_at: "2026-01-01T00:00:00+00:00"
        generated_by: "tracevault"
        generator_version: "0.1.0"
        schema_version: "wiki-export-v1"
        source_policy: "raw_text_authoritative"
        validation_status: "validated"
        evidence_count: 1
        ---

        # Test Note

        ## Claims

        - A fact [E1]

        ## Evidence References

        ### E1

        - **Document**: `doc_001`
        - **Chunk**: `chunk_001`

        ---

        ## TraceVault Metadata

        - note_id: `{note_id}`
    ''')


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tracevault", "wiki-health"] + list(args),
        capture_output=True,
        text=True,
    )


class TestCLIHelp:
    def test_help_exits_zero(self):
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "wiki" in result.stdout.lower()

    def test_help_shows_options(self):
        result = _run_cli("--help")
        assert "--json" in result.stdout
        assert "--source-manifest" in result.stdout
        assert "--strict" in result.stdout


class TestCLICleanWiki:
    def test_valid_directory_exits_zero(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        result = _run_cli(str(tmp_path))
        assert result.returncode == 0

    def test_valid_directory_shows_passed(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        result = _run_cli(str(tmp_path))
        assert "PASSED" in result.stdout

    def test_valid_directory_json(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        result = _run_cli(str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["passed"] is True
        assert data["error_count"] == 0


class TestCLIBadWiki:
    def test_error_directory_exits_one(self, tmp_path: Path):
        (tmp_path / "bad.md").write_text("# No frontmatter")
        result = _run_cli(str(tmp_path))
        assert result.returncode == 1

    def test_error_directory_shows_failed(self, tmp_path: Path):
        (tmp_path / "bad.md").write_text("# No frontmatter")
        result = _run_cli(str(tmp_path))
        assert "FAILED" in result.stdout

    def test_error_directory_json(self, tmp_path: Path):
        (tmp_path / "bad.md").write_text("# No frontmatter")
        result = _run_cli(str(tmp_path), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["passed"] is False
        assert data["error_count"] > 0


class TestCLIMissingPath:
    def test_nonexistent_path(self):
        result = _run_cli("/nonexistent/path/that/does/not/exist")
        assert result.returncode == 1


class TestCLIStrict:
    def test_strict_exits_one_on_warnings(self, tmp_path: Path):
        """validation_required produces a warning; --strict should exit 1."""
        content = _valid_note().replace(
            'validation_status: "validated"',
            'validation_status: "validation_required"',
        )
        (tmp_path / "note.md").write_text(content)
        result = _run_cli(str(tmp_path), "--strict")
        assert result.returncode == 1

    def test_without_strict_warnings_exit_zero(self, tmp_path: Path):
        content = _valid_note().replace(
            'validation_status: "validated"',
            'validation_status: "validation_required"',
        )
        (tmp_path / "note.md").write_text(content)
        result = _run_cli(str(tmp_path))
        assert result.returncode == 0


class TestCLISourceManifest:
    def test_missing_manifest_file(self):
        result = _run_cli("/tmp", "--source-manifest", "/nonexistent/manifest.json")
        assert result.returncode == 1

    def test_valid_manifest_no_mismatch(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"documents": [
            {"document_id": "doc_001", "content_hash": "abc123"},
        ]}))
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest))
        # Should not error since note doesn't have source_raw_hash in body
        assert result.returncode == 0


class TestCLIJSONOutput:
    def test_json_always_valid(self, tmp_path: Path):
        """Even on error, JSON output should be valid."""
        (tmp_path / "bad.md").write_text("# No frontmatter")
        result = _run_cli(str(tmp_path), "--json")
        # Should parse without error
        data = json.loads(result.stdout)
        assert "passed" in data
        assert "issues" in data


class TestCLIMalformedYAML:
    """Regression: malformed YAML must not produce traceback, must exit 1."""

    def test_malformed_yaml_exits_one(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: [unterminated
            ---
            # Bad
        ''')
        (tmp_path / "bad.md").write_text(content)
        result = _run_cli(str(tmp_path))
        assert result.returncode == 1
        assert "Traceback" not in result.stdout
        assert "Traceback" not in result.stderr

    def test_malformed_yaml_json_valid(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: [unterminated
            ---
            # Bad
        ''')
        (tmp_path / "bad.md").write_text(content)
        result = _run_cli(str(tmp_path), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["passed"] is False
        assert data["error_count"] > 0
        # The issue code should be malformed_frontmatter
        assert any(i["code"] == "malformed_frontmatter" for i in data["issues"])

    def test_malformed_yaml_no_traceback_in_stderr(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            key: :invalid: yaml: [
            ---
            # Body
        ''')
        (tmp_path / "bad.md").write_text(content)
        result = _run_cli(str(tmp_path))
        assert "Traceback" not in result.stderr


class TestCLISingleFile:
    """Regression: CLI must accept single .md file without NotADirectoryError."""

    def test_single_valid_file_exits_zero(self, tmp_path: Path):
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        result = _run_cli(str(note_file))
        assert result.returncode == 0
        assert "PASSED" in result.stdout

    def test_single_valid_file_json(self, tmp_path: Path):
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        result = _run_cli(str(note_file), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["passed"] is True
        assert data["files_scanned"] == 1

    def test_single_invalid_file_exits_one(self, tmp_path: Path):
        note_file = tmp_path / "bad.md"
        note_file.write_text("# No frontmatter")
        result = _run_cli(str(note_file), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["passed"] is False
        assert data["files_scanned"] == 1

    def test_single_file_no_notadirectoryerror(self, tmp_path: Path):
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        result = _run_cli(str(note_file))
        # Must not raise NotADirectoryError
        assert "NotADirectoryError" not in result.stderr
        assert result.returncode == 0

    def test_single_malformed_yaml_file_json(self, tmp_path: Path):
        note_file = tmp_path / "bad.md"
        note_file.write_text("---\nnote_id: [broken\n---\n# Bad")
        result = _run_cli(str(note_file), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["passed"] is False


class TestCLISourceManifestRealSchema:
    """Regression: --source-manifest must support real TraceVault ingestion schema."""

    def test_real_manifest_entries_schema(self, tmp_path: Path):
        """Manifest with 'entries' list should be recognized."""
        (tmp_path / "note.md").write_text(_valid_note())
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "version": "1.0",
            "entries": [
                {
                    "source_path": "docs/test.md",
                    "content_hash": "abc123",
                    "size_bytes": 100,
                    "modified_time": "2026-01-01T00:00:00",
                    "last_ingested": "2026-01-01T00:00:00",
                },
            ],
        }))
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest))
        # Should not crash, should process without error
        assert result.returncode == 0

    def test_real_manifest_no_documents_key(self, tmp_path: Path):
        """Manifest without 'documents' key should not silently no-op."""
        (tmp_path / "note.md").write_text(_valid_note())
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "version": "1.0",
            "entries": [
                {
                    "source_path": "docs/test.md",
                    "content_hash": "abc123",
                    "size_bytes": 100,
                    "modified_time": "2026-01-01T00:00:00",
                    "last_ingested": "2026-01-01T00:00:00",
                },
            ],
        }))
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        # Should not error (note doesn't have source_documents to check against)
        data = json.loads(result.stdout)
        assert "passed" in data

    def test_unrecognized_manifest_schema_warning(self, tmp_path: Path):
        """Manifest with no entries or documents list should produce structured issue."""
        (tmp_path / "note.md").write_text(_valid_note())
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "version": "1.0",
            "unknown_key": "no entries or documents here",
        }))
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest))
        # Should not crash
        assert "Traceback" not in result.stderr
        # Now exits 1 because source_manifest_unrecognized is an ERROR
        assert result.returncode == 1


class TestCLIPathNotFound:
    def test_single_file_not_found(self):
        result = _run_cli("/nonexistent/file.md")
        assert result.returncode == 1

    def test_single_file_not_found_json(self):
        result = _run_cli("/nonexistent/file.md", "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data


class TestCLIUnrecognizedManifestJSON:
    """Regression: unrecognized manifest shape must not break --json contract."""

    def _bad_manifest(self, tmp_path: Path) -> tuple[Path, Path]:
        note = tmp_path / "note.md"
        note.write_text(_valid_note())
        manifest = tmp_path / "bad-manifest.json"
        manifest.write_text(json.dumps({
            "version": "1.0",
            "unknown_key": "not a valid manifest shape",
        }))
        return note, manifest

    def test_json_exactly_one_document(self, tmp_path: Path):
        """--json output must be parseable as a single JSON document."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        # Must parse without error (exactly one top-level JSON object)
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_json_contains_source_manifest_unrecognized(self, tmp_path: Path):
        """The unrecognized manifest issue must appear in the report."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        data = json.loads(result.stdout)
        assert any(
            i["code"] == "source_manifest_unrecognized" for i in data.get("issues", [])
        )

    def test_json_exit_code_is_one(self, tmp_path: Path):
        """Unrecognized manifest shape is an ERROR, exit code must be 1."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        assert result.returncode == 1

    def test_json_error_count_includes_manifest_issue(self, tmp_path: Path):
        """error_count in the final JSON report must include the manifest issue."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        data = json.loads(result.stdout)
        assert data["error_count"] >= 1
        assert data["passed"] is False

    def test_human_output_no_traceback(self, tmp_path: Path):
        """Non-JSON mode should show issue through normal report, no traceback."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest))
        assert "Traceback" not in result.stderr
        assert "Traceback" not in result.stdout
        assert result.returncode == 1

    def test_no_double_json_on_stdout(self, tmp_path: Path):
        """stdout must contain exactly one JSON object, not two."""
        _note, manifest = self._bad_manifest(tmp_path)
        result = _run_cli(str(tmp_path), "--source-manifest", str(manifest), "--json")
        # If there were two JSON objects on stdout, json.loads would succeed
        # on the first one but there'd be trailing content. Verify clean parse.
        parsed = json.loads(result.stdout)
        # Re-serialize and compare to ensure it round-trips cleanly
        re_round = json.dumps(parsed, indent=2)
        reparsed = json.loads(re_round)
        assert reparsed == parsed
