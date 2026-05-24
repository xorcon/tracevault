"""Tests for wiki health report models (report.py)."""

import dataclasses

import pytest

from tracevault.wiki.report import (
    IssueSeverity,
    WikiHealthReport,
    WikiLintIssue,
    WikiParsedNote,
)


class TestWikiLintIssue:
    def test_creation(self):
        issue = WikiLintIssue(
            code="missing_frontmatter",
            severity=IssueSeverity.ERROR,
            message="No YAML frontmatter",
            file_path="test.md",
        )
        assert issue.code == "missing_frontmatter"
        assert issue.severity is IssueSeverity.ERROR
        assert issue.message == "No YAML frontmatter"
        assert issue.file_path == "test.md"

    def test_default_file_path(self):
        issue = WikiLintIssue(
            code="missing_frontmatter",
            severity=IssueSeverity.ERROR,
            message="Test",
        )
        assert issue.file_path == ""

    def test_frozen(self):
        issue = WikiLintIssue(
            code="missing_frontmatter",
            severity=IssueSeverity.ERROR,
            message="Test",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            issue.message = "changed"  # type: ignore

    def test_warning_severity(self):
        issue = WikiLintIssue(
            code="orphan_note",
            severity=IssueSeverity.WARNING,
            message="Orphaned note",
        )
        assert issue.severity is IssueSeverity.WARNING


class TestWikiParsedNote:
    def test_defaults(self):
        note = WikiParsedNote(file_path="test.md")
        assert note.frontmatter == {}
        assert note.raw_frontmatter == ""
        assert note.body == ""
        assert note.evidence_labels == []
        assert note.claim_citations == {}

    def test_full(self):
        note = WikiParsedNote(
            file_path="test.md",
            frontmatter={"note_id": "n1"},
            raw_frontmatter="note_id: n1",
            body="# Title",
            evidence_labels=["E1"],
            claim_citations={"A fact": ["E1"]},
        )
        assert note.frontmatter["note_id"] == "n1"
        assert note.evidence_labels == ["E1"]
        assert note.claim_citations["A fact"] == ["E1"]


class TestWikiHealthReport:
    def test_empty_report(self):
        report = WikiHealthReport(path="/tmp/wiki")
        assert report.files_scanned == 0
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.passed is True

    def test_error_count(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            files_scanned=2,
            issues=[
                WikiLintIssue(
                    code="missing_frontmatter",
                    severity=IssueSeverity.ERROR,
                    message="No frontmatter",
                    file_path="a.md",
                ),
                WikiLintIssue(
                    code="missing_frontmatter",
                    severity=IssueSeverity.ERROR,
                    message="No frontmatter",
                    file_path="b.md",
                ),
            ],
        )
        assert report.error_count == 2
        assert report.passed is False

    def test_warning_count(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            issues=[
                WikiLintIssue(
                    code="orphan_note",
                    severity=IssueSeverity.WARNING,
                    message="Orphan",
                    file_path="a.md",
                ),
            ],
        )
        assert report.warning_count == 1
        assert report.passed is True  # warnings alone don't fail

    def test_mixed_issues(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            issues=[
                WikiLintIssue(
                    code="missing_frontmatter",
                    severity=IssueSeverity.ERROR,
                    message="Error",
                    file_path="a.md",
                ),
                WikiLintIssue(
                    code="orphan_note",
                    severity=IssueSeverity.WARNING,
                    message="Warning",
                    file_path="b.md",
                ),
            ],
        )
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.passed is False

    def test_summary(self):
        report = WikiHealthReport(path="/tmp/wiki", files_scanned=3)
        summary = report.summary()
        assert summary["path"] == "/tmp/wiki"
        assert summary["files_scanned"] == 3
        assert summary["error_count"] == 0
        assert summary["warning_count"] == 0
        assert summary["passed"] is True

    def test_to_dict(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            files_scanned=1,
            issues=[
                WikiLintIssue(
                    code="missing_frontmatter",
                    severity=IssueSeverity.ERROR,
                    message="No frontmatter",
                    file_path="a.md",
                ),
            ],
        )
        d = report.to_dict()
        assert d["path"] == "/tmp/wiki"
        assert d["files_scanned"] == 1
        assert d["error_count"] == 1
        assert d["passed"] is False
        assert len(d["issues"]) == 1
        assert d["issues"][0]["code"] == "missing_frontmatter"
        assert d["issues"][0]["severity"] == "error"

    def test_to_dict_empty_issues(self):
        report = WikiHealthReport(path="/tmp/wiki", files_scanned=0)
        d = report.to_dict()
        assert d["issues"] == []


class TestIssueSeverity:
    def test_error_value(self):
        assert IssueSeverity.ERROR.value == "error"

    def test_warning_value(self):
        assert IssueSeverity.WARNING.value == "warning"


class TestSourceManifestUnrecognizedIssue:
    """Regression: source_manifest_unrecognized must be representable as structured issue."""

    def test_can_create_structured_issue(self):
        issue = WikiLintIssue(
            code="source_manifest_unrecognized",
            severity=IssueSeverity.ERROR,
            message="Source manifest has unrecognized schema",
            file_path="/tmp/manifest.json",
        )
        assert issue.code == "source_manifest_unrecognized"
        assert issue.severity is IssueSeverity.ERROR

    def test_report_error_count_includes_manifest_issue(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            files_scanned=1,
            issues=[
                WikiLintIssue(
                    code="source_manifest_unrecognized",
                    severity=IssueSeverity.ERROR,
                    message="Unrecognized schema",
                    file_path="/tmp/manifest.json",
                ),
            ],
        )
        assert report.error_count == 1
        assert report.passed is False

    def test_to_dict_includes_manifest_issue(self):
        report = WikiHealthReport(
            path="/tmp/wiki",
            files_scanned=1,
            issues=[
                WikiLintIssue(
                    code="source_manifest_unrecognized",
                    severity=IssueSeverity.ERROR,
                    message="Unrecognized schema",
                    file_path="/tmp/manifest.json",
                ),
            ],
        )
        d = report.to_dict()
        assert len(d["issues"]) == 1
        assert d["issues"][0]["code"] == "source_manifest_unrecognized"
        assert d["issues"][0]["severity"] == "error"
