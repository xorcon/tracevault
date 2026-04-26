"""Ingest manifest management.

Handles persistence of ingestion state for differential ingest detection.
"""

import json
from pathlib import Path
from typing import Optional

from tracevault.ingestion.models import ManifestEntry

DEFAULT_MANIFEST_PATH = ".tracevault/ingest-manifest.json"


class IngestManifest:
    """Manages the ingestion manifest.

    The manifest tracks source files by normalized path to detect:
    - new files
    - unchanged files
    - changed files
    """

    def __init__(self, manifest_path: Path | str):
        """Initialize manifest.

        Args:
            manifest_path: Path to manifest JSON file.
        """
        self.manifest_path = Path(manifest_path)
        self._entries: dict[str, ManifestEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load manifest from disk."""
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                self._entries = {
                    entry["source_path"]: ManifestEntry(**entry)
                    for entry in data.get("entries", [])
                }
            except (json.JSONDecodeError, KeyError):
                # Corrupted manifest - start fresh
                self._entries = {}

    def save(self) -> None:
        """Save manifest to disk."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "entries": [entry.__dict__ for entry in self._entries.values()],
        }
        self.manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_entry(self, source_path: str) -> Optional[ManifestEntry]:
        """Get manifest entry for source path.

        Args:
            source_path: Normalized source path.

        Returns:
            ManifestEntry if exists, None otherwise.
        """
        return self._entries.get(source_path)

    def update_entry(
        self,
        source_path: str,
        content_hash: str,
        size_bytes: int,
        modified_time: str,
        ingested_at: str,
    ) -> str:
        """Update or create manifest entry.

        Args:
            source_path: Normalized source path.
            content_hash: SHA-256 hash of content.
            size_bytes: File size.
            modified_time: File modification time.
            ingested_at: Ingestion timestamp.

        Returns:
            Status: 'new', 'unchanged', or 'changed'.
        """
        existing = self._entries.get(source_path)

        if existing is None:
            status = "new"
        elif existing.content_hash == content_hash:
            status = "unchanged"
        else:
            status = "changed"

        self._entries[source_path] = ManifestEntry(
            source_path=source_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            modified_time=modified_time,
            last_ingested=ingested_at,
        )

        return status

    def remove_entry(self, source_path: str) -> bool:
        """Remove entry from manifest.

        Args:
            source_path: Path to remove.

        Returns:
            True if entry existed and was removed.
        """
        if source_path in self._entries:
            del self._entries[source_path]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def get_all_entries(self) -> list[ManifestEntry]:
        """Get all manifest entries."""
        return list(self._entries.values())

    def normalize_path(self, path: Path | str) -> str:
        """Normalize path for manifest storage.

        Converts to relative path with forward slashes.
        """
        p = Path(path)
        # Make relative if possible, otherwise use absolute
        try:
            rel_path = p.relative_to(Path.cwd())
        except ValueError:
            rel_path = p
        return str(rel_path).replace("\\", "/")
