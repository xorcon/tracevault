"""Wiki export module.

Phase 6A — Evidence-backed Wiki Export.

Provides a non-destructive Markdown wiki export layer that turns
evidence-backed structured inputs into Markdown knowledge notes
while preserving claim-to-evidence mapping and TraceVault metadata.

A wiki note is a derived knowledge artifact, not a source of truth.
"""

from tracevault.wiki.exporter import export_note, export_notes
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
from tracevault.wiki.slug import generate_slug

__all__ = [
    # Models
    "WikiNote",
    "WikiClaim",
    "WikiEvidenceReference",
    "WikiExportMetadata",
    "WikiExportResult",
    "WikiSourceDocument",
    "WikiSourceChunk",
    # Markdown
    "render_note",
    # Slug
    "generate_slug",
    # Exporter
    "export_note",
    "export_notes",
]
