"""Deterministic index note generation for Obsidian vault.

Index notes are metadata-only: they parse frontmatter fields and build
links to the copied notes.  They do not summarize, infer relationships,
or generate new knowledge.
"""

from pathlib import Path

from tracevault.wiki.vault.layout import resolve_index_destination
from tracevault.wiki.vault.models import (
    VaultIndexPlan,
    VaultNotePlan,
)

INDEX_FILES = [
    "Home.md",
    "By-Type.md",
    "By-Source.md",
]


def build_index_plans(
    vault_dir: Path,
    note_plans: list[VaultNotePlan],
) -> list[VaultIndexPlan]:
    """Build index note plans from accepted (non-rejected, non-skipped) notes.

    Returns a deterministic list of VaultIndexPlan objects, one per
    index file, sorted by filename.
    """
    accepted = [n for n in note_plans if not n.rejected and not n.skipped]
    plans: list[VaultIndexPlan] = []

    for filename in sorted(INDEX_FILES):
        dest = resolve_index_destination(vault_dir, filename)
        plans.append(VaultIndexPlan(
            destination_path=str(dest),
            relative_destination=str(dest.relative_to(vault_dir)),
            filename=filename,
            num_entries=len(accepted),
        ))

    return plans


def render_home_index(note_plans: list[VaultNotePlan]) -> str:
    """Render the Home.md index note content.

    Lists all accepted notes with Obsidian-style wikilinks.
    """
    accepted = [n for n in note_plans if not n.rejected and not n.skipped]
    accepted.sort(key=lambda n: n.title or n.note_id)

    lines: list[str] = []
    lines.append("---")
    lines.append("title: \"TraceVault Home\"")
    lines.append("type: \"vault_index\"")
    lines.append("---")
    lines.append("")
    lines.append("# TraceVault Home")
    lines.append("")
    lines.append("Auto-generated vault index. Do not edit manually.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")

    for note in accepted:
        link_path = note.relative_destination.replace("TraceVault/Notes/", "")
        title = note.title or note.note_id or note.original_filename
        lines.append(f"- [[{link_path}|{title}]]")

    lines.append("")
    lines.append("<!-- tracevault-generated: vault-index -->")
    return "\n".join(lines)


def render_by_type_index(note_plans: list[VaultNotePlan]) -> str:
    """Render the By-Type.md index note content.

    Groups accepted notes by note_type from frontmatter.
    """
    accepted = [n for n in note_plans if not n.rejected and not n.skipped]

    by_type: dict[str, list[VaultNotePlan]] = {}
    for note in accepted:
        note_type = note.note_type or "unknown"
        by_type.setdefault(note_type, []).append(note)

    lines: list[str] = []
    lines.append("---")
    lines.append("title: \"Notes by Type\"")
    lines.append("type: \"vault_index\"")
    lines.append("---")
    lines.append("")
    lines.append("# Notes by Type")
    lines.append("")
    lines.append("Auto-generated index grouped by note type.")
    lines.append("")

    for note_type in sorted(by_type):
        lines.append(f"## {note_type}")
        lines.append("")
        for note in sorted(by_type[note_type], key=lambda n: n.title or n.note_id):
            link_path = note.relative_destination.replace("TraceVault/Notes/", "")
            title = note.title or note.note_id or note.original_filename
            lines.append(f"- [[{link_path}|{title}]]")
        lines.append("")

    lines.append("<!-- tracevault-generated: vault-index -->")
    return "\n".join(lines)


def render_by_source_index(note_plans: list[VaultNotePlan]) -> str:
    """Render the By-Source.md index note content.

    Groups accepted notes by source document_id from frontmatter.
    """
    accepted = [n for n in note_plans if not n.rejected and not n.skipped]

    by_source: dict[str, list[VaultNotePlan]] = {}
    for note in accepted:
        for doc_id in note.source_document_ids or ["<no-source>"]:
            by_source.setdefault(doc_id, []).append(note)

    lines: list[str] = []
    lines.append("---")
    lines.append("title: \"Notes by Source\"")
    lines.append("type: \"vault_index\"")
    lines.append("---")
    lines.append("")
    lines.append("# Notes by Source")
    lines.append("")
    lines.append("Auto-generated index grouped by source document.")
    lines.append("")

    for doc_id in sorted(by_source):
        lines.append(f"## {doc_id}")
        lines.append("")
        for note in sorted(by_source[doc_id], key=lambda n: n.title or n.note_id):
            link_path = note.relative_destination.replace("TraceVault/Notes/", "")
            title = note.title or note.note_id or note.original_filename
            lines.append(f"- [[{link_path}|{title}]]")
        lines.append("")

    lines.append("<!-- tracevault-generated: vault-index -->")
    return "\n".join(lines)


def render_index_note(filename: str, note_plans: list[VaultNotePlan]) -> str:
    """Render the content for a specific index note file."""
    if filename == "Home.md":
        return render_home_index(note_plans)
    elif filename == "By-Type.md":
        return render_by_type_index(note_plans)
    elif filename == "By-Source.md":
        return render_by_source_index(note_plans)
    raise ValueError(f"Unknown index file: {filename}")
