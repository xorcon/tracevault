"""Tests for directory-level wiki health check (health.py)."""

import textwrap
from pathlib import Path

import pytest

from tracevault.wiki.health import check_wiki_health


def _valid_note(name: str = "note.md", note_id: str = "note_001") -> str:
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


class TestCleanDirectory:
    def test_single_valid_note(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 1
        assert report.passed is True
        assert report.error_count == 0

    def test_multiple_valid_notes(self, tmp_path: Path):
        (tmp_path / "note_a.md").write_text(_valid_note(note_id="note_a"))
        (tmp_path / "note_b.md").write_text(_valid_note(note_id="note_b"))
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 2
        assert report.passed is True

    def test_empty_directory(self, tmp_path: Path):
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 0
        assert report.passed is True
        assert report.issues == []

    def test_subdirectory_notes(self, tmp_path: Path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "note.md").write_text(_valid_note())
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 1
        assert report.passed is True

    def test_hidden_directory_skipped(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "note.md").write_text(_valid_note())
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 0


class TestDuplicateNoteId:
    def test_duplicate_detected(self, tmp_path: Path):
        (tmp_path / "note_a.md").write_text(_valid_note(note_id="note_001"))
        (tmp_path / "note_b.md").write_text(_valid_note(note_id="note_001"))
        report = check_wiki_health(tmp_path)
        assert any(i.code == "duplicate_note_id" for i in report.issues)
        assert report.passed is False

    def test_unique_ids_pass(self, tmp_path: Path):
        (tmp_path / "note_a.md").write_text(_valid_note(note_id="note_a"))
        (tmp_path / "note_b.md").write_text(_valid_note(note_id="note_b"))
        report = check_wiki_health(tmp_path)
        assert not any(i.code == "duplicate_note_id" for i in report.issues)


class TestOrphanNote:
    def test_orphan_no_frontmatter(self, tmp_path: Path):
        (tmp_path / "orphan.md").write_text("# Just a note\n\nNo frontmatter.")
        report = check_wiki_health(tmp_path)
        assert any(i.code == "orphan_note" for i in report.issues)

    def test_orphan_malformed_frontmatter(self, tmp_path: Path):
        (tmp_path / "orphan.md").write_text("---\nnote_id: val\n# No closing")
        report = check_wiki_health(tmp_path)
        assert any(i.code == "orphan_note" for i in report.issues)


class TestDeterministicOutput:
    def test_issues_sorted_by_file_path(self, tmp_path: Path):
        # Create notes with issues in a specific order
        (tmp_path / "b.md").write_text("# No FM")
        (tmp_path / "a.md").write_text("# No FM")
        report = check_wiki_health(tmp_path)
        file_paths = [i.file_path for i in report.issues]
        assert file_paths == sorted(file_paths)

    def test_parsed_notes_deterministic_order(self, tmp_path: Path):
        (tmp_path / "b.md").write_text(_valid_note(note_id="b"))
        (tmp_path / "a.md").write_text(_valid_note(note_id="a"))
        report = check_wiki_health(tmp_path)
        paths = [n.file_path for n in report.parsed_notes]
        assert paths == sorted(paths)


class TestMixedIssues:
    def test_valid_and_invalid_notes(self, tmp_path: Path):
        (tmp_path / "good.md").write_text(_valid_note(note_id="good"))
        (tmp_path / "bad.md").write_text("# Bad note")
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 2
        assert report.error_count > 0
        assert report.passed is False

    def test_error_and_warning_count(self, tmp_path: Path):
        (tmp_path / "orphan.md").write_text("# No frontmatter")
        report = check_wiki_health(tmp_path)
        # missing_frontmatter is ERROR, orphan_note is WARNING
        assert report.error_count >= 1
        assert report.warning_count >= 1


class TestNonMdFiles:
    def test_txt_files_ignored(self, tmp_path: Path):
        (tmp_path / "note.txt").write_text("Not a markdown file")
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 0

    def test_mixed_files(self, tmp_path: Path):
        (tmp_path / "note.md").write_text(_valid_note())
        (tmp_path / "readme.txt").write_text("Not wiki")
        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 1


class TestSourceHashes:
    def test_source_hashes_passed_through(self, tmp_path: Path):
        """Source hashes should be forwarded to lint_note without error."""
        (tmp_path / "note.md").write_text(_valid_note())
        report = check_wiki_health(tmp_path, source_hashes={"doc_001": "abc"})
        # No error since the note doesn't have source_raw_hash in evidence section
        # but the check runs without crashing
        assert report.files_scanned == 1


class TestSingleFileInput:
    """Regression: check_wiki_health must accept a single .md file."""

    def test_single_valid_file(self, tmp_path: Path):
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        report = check_wiki_health(note_file)
        assert report.files_scanned == 1
        assert report.passed is True
        assert report.error_count == 0
        assert report.path == str(note_file)

    def test_single_invalid_file(self, tmp_path: Path):
        note_file = tmp_path / "bad.md"
        note_file.write_text("# No frontmatter")
        report = check_wiki_health(note_file)
        assert report.files_scanned == 1
        assert report.passed is False
        assert report.error_count >= 1

    def test_single_file_no_notadirectoryerror(self, tmp_path: Path):
        """Must not raise NotADirectoryError for file input."""
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        # Should not raise
        report = check_wiki_health(note_file)
        assert report.files_scanned == 1

    def test_single_file_with_source_hashes(self, tmp_path: Path):
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        report = check_wiki_health(note_file, source_hashes={"doc_001": "abc"})
        assert report.files_scanned == 1

    def test_single_non_md_file(self, tmp_path: Path):
        """Non-.md file should produce a warning, not crash."""
        note_file = tmp_path / "note.txt"
        note_file.write_text("Not markdown")
        report = check_wiki_health(note_file)
        assert report.files_scanned == 1
        # Should have a warning about non-Markdown file
        assert report.warning_count >= 1

    def test_single_file_no_cross_note_checks(self, tmp_path: Path):
        """Single file should not produce orphan_note or duplicate_note_id."""
        note_file = tmp_path / "note.md"
        note_file.write_text(_valid_note())
        report = check_wiki_health(note_file)
        assert not any(i.code == "orphan_note" for i in report.issues)
        assert not any(i.code == "duplicate_note_id" for i in report.issues)


class TestNonexistentPath:
    def test_nonexistent_path(self, tmp_path: Path):
        bad_path = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            check_wiki_health(bad_path)


class TestExcludeDirs:
    """exclude_dirs parameter must skip generated vault output."""

    def test_exclude_dir_skips_nested_directory(self, tmp_path: Path):
        (tmp_path / "good.md").write_text(_valid_note(note_id="good"))
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "bad.md").write_text("# No frontmatter")

        report = check_wiki_health(tmp_path, exclude_dirs=[bad_dir.resolve()])
        assert report.files_scanned == 1
        assert report.passed is True

    def test_without_exclude_dir_bad_file_detected(self, tmp_path: Path):
        (tmp_path / "good.md").write_text(_valid_note(note_id="good"))
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "bad.md").write_text("# No frontmatter")

        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 2
        assert report.passed is False

    def test_exclude_dirs_deep_nesting(self, tmp_path: Path):
        (tmp_path / "top.md").write_text(_valid_note(note_id="top"))
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "bad.md").write_text("# No frontmatter")

        exclude = tmp_path / "a"
        report = check_wiki_health(tmp_path, exclude_dirs=[exclude.resolve()])
        assert report.files_scanned == 1
        assert report.passed is True

    def test_tracevault_dir_skipped(self, tmp_path: Path):
        (tmp_path / "good.md").write_text(_valid_note(note_id="good"))
        tv = tmp_path / "TraceVault" / "Notes"
        tv.mkdir(parents=True)
        (tv / "generated.md").write_text("# Generated vault output")

        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 1
        assert report.passed is True

    def test_tracevault_dir_at_nested_level_skipped(self, tmp_path: Path):
        (tmp_path / "sub" / "good.md").parent.mkdir()
        (tmp_path / "sub" / "good.md").write_text(_valid_note(note_id="good"))
        (tmp_path / "sub" / "TraceVault" / "Notes").mkdir(parents=True)
        (tmp_path / "sub" / "TraceVault" / "Notes" / "generated.md").write_text(
            "no frontmatter"
        )

        report = check_wiki_health(tmp_path)
        assert report.files_scanned == 1

    def test_single_file_under_excluded_dir_returns_empty(self, tmp_path: Path):
        bad_dir = tmp_path / "excluded"
        bad_dir.mkdir()
        bad_file = bad_dir / "bad.md"
        bad_file.write_text("# No frontmatter")

        report = check_wiki_health(
            bad_file, exclude_dirs=[bad_dir.resolve()]
        )
        assert report.files_scanned == 0
        assert report.passed is True

    def test_exclude_dir_prevents_generated_vault_health_failure(
        self, tmp_path: Path
    ):
        """The core Phase 6C scenario: vault_dir nested in wiki_dir."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = wiki_dir / "vault"
        (wiki_dir / "sources").mkdir(parents=True)

        # One valid source note
        (wiki_dir / "sources" / "real.md").write_text(
            _valid_note(note_id="real")
        )

        # Generated vault output with invalid Markdown under non-TraceVault dir
        # (TraceVault dir is skipped by default; vault_dir needs exclude_dirs)
        (vault_dir / "output" / "Notes").mkdir(parents=True)
        (vault_dir / "output" / "Notes" / "generated.md").write_text(
            "this has no frontmatter and would fail health"
        )

        # Without exclude_dirs, the non-TraceVault output dir is scanned
        report_no_exclude = check_wiki_health(wiki_dir)
        assert report_no_exclude.passed is False

        # With exclude_dirs, only source notes are checked
        report_with_exclude = check_wiki_health(
            wiki_dir, exclude_dirs=[vault_dir.resolve()]
        )
        assert report_with_exclude.passed is True
        assert report_with_exclude.files_scanned == 1
