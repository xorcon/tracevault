"""Non-destructive wiki export with evidence contract validation.

Proposal-first export: generates candidate Markdown content without
overwriting existing files unless explicitly allowed.

In strict mode (default), the exporter rejects:
- Notes without validated metadata (validation_status != "validated")
- Notes where note.note_id != metadata.note_id (identity mismatch)
- Claims marked supported (unsupported=False) but with no evidence_refs
- Claims explicitly marked unsupported
"""

from pathlib import Path

from tracevault.wiki.markdown import render_note
from tracevault.wiki.models import WikiExportResult, WikiNote
from tracevault.wiki.slug import generate_slug


def build_note_filename(note: WikiNote) -> str:
    """Build a deterministic, filename-safe export filename for a note.

    Uses ``{title-slug}-{note-id-slug}.md`` so that distinct notes with
    colliding titles land on different files.  Falls back to a
    note-id-only filename when the title is empty or whitespace-only.

    The canonical ``note.note_id`` is used (not ``metadata.note_id``)
    so that pathing stays consistent even when strict validation is
    disabled.
    """
    note_id_slug = generate_slug(note.note_id)

    if not note.title.strip():
        return f"{note_id_slug}.md"

    title_slug = generate_slug(note.title)
    return f"{title_slug}-{note_id_slug}.md"


def export_note(
    note: WikiNote,
    output_dir: Path | str,
    *,
    allow_overwrite: bool = False,
    strict: bool = True,
    allow_unvalidated: bool = False,
    allow_unsupported: bool = False,
) -> WikiExportResult:
    """Export a single WikiNote to a Markdown file.

    Non-destructive by default:
    - If the target file exists and allow_overwrite is False, the file
      is skipped and the result is returned with skipped=True.

    In strict mode (default), the exporter enforces the evidence contract:
    - Notes without validated metadata are rejected
    - Notes with note.note_id != metadata.note_id are rejected
    - Claims marked supported but with no evidence_refs are rejected
    - Claims explicitly marked unsupported are rejected

    Args:
        note: The WikiNote to export.
        output_dir: Directory to write the Markdown file into.
        allow_overwrite: If True, overwrite existing files.
        strict: If True (default), enforce full evidence/validation contract.
        allow_unvalidated: If True, allow notes with validation_status != "validated".
        allow_unsupported: If True, allow unsupported claims in the note.

    Returns:
        WikiExportResult with rendered Markdown and write/reject status.
    """
    output_dir = Path(output_dir)
    file_path = output_dir / build_note_filename(note)

    # Validation contract checks (strict mode)
    if strict:
        # Check validation status
        if not allow_unvalidated:
            meta = note.metadata
            if meta is None or meta.validation_status != "validated":
                return _rejected(
                    note_id=note.note_id,
                    file_path=str(file_path),
                    reason="Note is not validated",
                )

        # Identity consistency: note.note_id must match metadata.note_id
        meta = note.metadata
        if meta is not None and meta.note_id != note.note_id:
            return _rejected(
                note_id=note.note_id,
                file_path=str(file_path),
                reason=(
                    f"note_id mismatch: note.note_id '{note.note_id}' does not "
                    f"match metadata.note_id '{meta.note_id}'"
                ),
            )

        # Check for invalid supported claims (no evidence refs)
        for claim in note.invalid_supported_claims():
            return _rejected(
                note_id=note.note_id,
                file_path=str(file_path),
                reason=(
                    f"Claim '{claim.statement}' is supported but has no "
                    "evidence refs"
                ),
            )

        # Check for unsupported claims
        if not allow_unsupported:
            for claim in note.unsupported_claims():
                return _rejected(
                    note_id=note.note_id,
                    file_path=str(file_path),
                    reason=(
                        f"Unsupported claim: '{claim.statement}'"
                    ),
                )

    markdown = render_note(note)

    # File existence check (non-destructive)
    if file_path.exists() and not allow_overwrite:
        return WikiExportResult(
            note_id=note.note_id,
            file_path=str(file_path),
            markdown=markdown,
            written=False,
            skipped=True,
            reason="File already exists",
        )

    # Write
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(markdown, encoding="utf-8")

    return WikiExportResult(
        note_id=note.note_id,
        file_path=str(file_path),
        markdown=markdown,
        written=True,
    )


def export_notes(
    notes: list[WikiNote],
    output_dir: Path | str,
    *,
    allow_overwrite: bool = False,
    strict: bool = True,
    allow_unvalidated: bool = False,
    allow_unsupported: bool = False,
) -> list[WikiExportResult]:
    """Export multiple WikiNotes.

    Args:
        notes: List of WikiNote objects to export.
        output_dir: Directory to write Markdown files into.
        allow_overwrite: If True, overwrite existing files.
        strict: If True (default), enforce full evidence/validation contract.
        allow_unvalidated: If True, allow unvalidated notes.
        allow_unsupported: If True, allow unsupported claims.

    Returns:
        List of WikiExportResult objects, one per note.
    """
    results: list[WikiExportResult] = []
    for note in notes:
        result = export_note(
            note,
            output_dir,
            allow_overwrite=allow_overwrite,
            strict=strict,
            allow_unvalidated=allow_unvalidated,
            allow_unsupported=allow_unsupported,
        )
        results.append(result)
    return results


def _rejected(
    note_id: str,
    file_path: str,
    reason: str,
) -> WikiExportResult:
    """Build a rejected export result."""
    return WikiExportResult(
        note_id=note_id,
        file_path=file_path,
        markdown="",
        written=False,
        skipped=False,
        rejected=True,
        reason=reason,
    )
