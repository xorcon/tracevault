"""Default Obsidian vault layout strategy.

Produces a deterministic directory structure:

    <vault-dir>/
      TraceVault/
        Notes/
          <original-phase-6a-filename>.md
        Index/
          Home.md
          By-Type.md
          By-Source.md
      tracevault-vault-manifest.json
"""

from pathlib import Path

NOTES_SUBDIR = "TraceVault/Notes"
INDEX_SUBDIR = "TraceVault/Index"
MANIFEST_FILENAME = "tracevault-vault-manifest.json"


def resolve_notes_dir(vault_dir: Path) -> Path:
    """Return the Notes subdirectory path."""
    return vault_dir / NOTES_SUBDIR


def resolve_index_dir(vault_dir: Path) -> Path:
    """Return the Index subdirectory path."""
    return vault_dir / INDEX_SUBDIR


def resolve_note_destination(vault_dir: Path, original_filename: str) -> Path:
    """Compute the destination path for a single wiki note.

    The original Phase 6A filename is preserved so that the hex-encoded
    note_id suffix remains unique and the content is not re-slugified.
    """
    return resolve_notes_dir(vault_dir) / original_filename


def resolve_index_destination(vault_dir: Path, index_filename: str) -> Path:
    """Compute the destination path for an index note."""
    return resolve_index_dir(vault_dir) / index_filename


def resolve_manifest_path(vault_dir: Path) -> Path:
    """Compute the destination path for the vault manifest JSON."""
    return vault_dir / MANIFEST_FILENAME
