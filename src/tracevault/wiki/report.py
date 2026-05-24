"""Deterministic wiki health report data models.

Defines structured types for lint issues, parsed wiki notes, and
aggregated health reports produced by Phase 6B validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class IssueSeverity(Enum):
    """Lint issue severity levels."""

    ERROR = "error"
    WARNING = "warning"


WikiLintIssueCode = Literal[
    "missing_frontmatter",
    "malformed_frontmatter",
    "missing_required_field",
    "invalid_note_type",
    "invalid_schema_version",
    "invalid_status",
    "invalid_source_policy",
    "invalid_validation_status",
    "evidence_count_mismatch",
    "claim_missing_citation",
    "citation_unresolved",
    "evidence_missing_document_id",
    "evidence_missing_chunk_id",
    "duplicate_evidence_label",
    "missing_tracevault_metadata",
    "duplicate_note_id",
    "orphan_note",
    "source_hash_mismatch",
    "source_hash_missing_expected",
    "source_manifest_unrecognized",
]


@dataclass(frozen=True)
class WikiLintIssue:
    """A single deterministic lint finding.

    Attributes:
        code: Stable, machine-readable issue identifier.
        severity: Whether this is an error or warning.
        message: Human-readable description.
        file_path: File path where the issue was found.
    """

    code: WikiLintIssueCode
    severity: IssueSeverity
    message: str
    file_path: str = ""


@dataclass
class WikiParsedNote:
    """Parsed representation of an exported wiki Markdown note.

    Produced by the parser, consumed by the linter.  Never mutates the
    source file content.

    Attributes:
        file_path: Absolute or relative path to the Markdown file.
        frontmatter: Parsed YAML frontmatter as a dict.
        raw_frontmatter: Raw frontmatter string before YAML parsing.
        body: Markdown body after the closing frontmatter delimiter.
        evidence_labels: Evidence section headings extracted from the body.
        claim_citations: Citations found in claim lines, keyed by claim text.
    """

    file_path: str
    frontmatter: dict = field(default_factory=dict)
    raw_frontmatter: str = ""
    body: str = ""
    evidence_labels: list[str] = field(default_factory=list)
    claim_citations: dict[str, list[str]] = field(default_factory=dict)
    yaml_parse_error: bool = False


@dataclass
class WikiHealthReport:
    """Aggregated health report for a directory scan.

    Attributes:
        path: Root directory that was scanned.
        files_scanned: Number of .md files processed.
        issues: All lint issues across all scanned files.
        parsed_notes: Parsed note objects, one per scanned file.
    """

    path: str
    files_scanned: int = 0
    issues: list[WikiLintIssue] = field(default_factory=list)
    parsed_notes: list[WikiParsedNote] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity is IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity is IssueSeverity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def summary(self) -> dict:
        """Return a summary dict for JSON serialization."""
        return {
            "path": self.path,
            "files_scanned": self.files_scanned,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed": self.passed,
        }

    def to_dict(self) -> dict:
        """Return a full dict representation for JSON output."""
        return {
            "path": self.path,
            "files_scanned": self.files_scanned,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed": self.passed,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "message": i.message,
                    "file_path": i.file_path,
                }
                for i in self.issues
            ],
        }
