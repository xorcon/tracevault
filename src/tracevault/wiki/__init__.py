"""Wiki export and health-check module.

Phase 6A — Evidence-backed Wiki Export
Phase 6B — Wiki Health / Lint / Drift Check

A wiki note is a derived knowledge artifact, not a source of truth.
"""

from tracevault.wiki.exporter import export_note, export_notes
from tracevault.wiki.health import check_wiki_health, print_health_report
from tracevault.wiki.lint import lint_note
from tracevault.wiki.markdown import render_note
from tracevault.wiki.models import (
    WikiClaim,
    WikiEvidenceReference,
    WikiExportMetadata,
    WikiExportResult,
    WikiNote,
    WikiSourceChunk,
    WikiSourceDocument,
)
from tracevault.wiki.parser import parse_wiki_note
from tracevault.wiki.report import (
    IssueSeverity,
    WikiHealthReport,
    WikiLintIssue,
    WikiParsedNote,
)
from tracevault.wiki.slug import generate_slug

__all__ = [
    # Phase 6A — Models
    "WikiNote",
    "WikiClaim",
    "WikiEvidenceReference",
    "WikiExportMetadata",
    "WikiExportResult",
    "WikiSourceDocument",
    "WikiSourceChunk",
    # Phase 6A — Rendering
    "render_note",
    "generate_slug",
    "export_note",
    "export_notes",
    # Phase 6B — Parser
    "parse_wiki_note",
    # Phase 6B — Lint
    "lint_note",
    # Phase 6B — Health
    "check_wiki_health",
    "print_health_report",
    # Phase 6B — Report models
    "IssueSeverity",
    "WikiHealthReport",
    "WikiLintIssue",
    "WikiParsedNote",
]
