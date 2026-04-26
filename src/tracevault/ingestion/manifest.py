"""Ingest manifest management.

Handles persistence of ingestion state for differential ingest detection.
"""

import json
from pathlib import Path
from typing import Optional

from tracevault.ingestion.models import ManifestEntry

DEFAULT_MANIFEST_PATH = ".tracevault/ingest-manifest.json"


class ManifestCorruptionError(Exception):
    """Raised when manifest file is corrupted or unreadable."""

    pass


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

        Raises:
            ManifestCorruptionError: If manifest exists but is invalid JSON.
        """
        self.manifest_path = Path(manifest_path)
        self._entries: dict[str, ManifestEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load manifest from disk.

        Raises:
            ManifestCorruptionError: If manifest file exists but contains invalid JSON
            or missing required fields.
        """
        if self.manifest_path.exists():
            try:
                content = self.manifest_path.read_text(encoding="utf-8")
                data = json.loads(content)
                entries = data.get("entries", [])
                if not isinstance(entries, list):
                    raise ManifestCorruptionError(
                        f"Manifest entries must be a list, got {type(entries).__name__}"
                    )
                # Normalize paths as keys to ensure canonical storage
                self._entries = {
                    self.normalize_path(entry["source_path"]): ManifestEntry(**entry)
                    for entry in entries
                }
            except json.JSONDecodeError as e:
                raise ManifestCorruptionError(
                    f"Invalid JSON in manifest: {e}"
                ) from e
            except KeyError as e:
                raise ManifestCorruptionError(
                    f"Missing required field in manifest entry: {e}"
                ) from e

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
            source_path: Source path (will be normalized).

        Returns:
            ManifestEntry if exists, None otherwise.
        """
        normalized = self.normalize_path(source_path)
        return self._entries.get(normalized)

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
            source_path: Source path (will be normalized).
            content_hash: SHA-256 hash of content.
            size_bytes: File size.
            modified_time: File modification time.
            ingested_at: Ingestion timestamp.

        Returns:
            Status: 'new', 'unchanged', or 'changed'.
        """
        # Normalize path to ensure canonical keying
        normalized_path = self.normalize_path(source_path)
        existing = self._entries.get(normalized_path)

        if existing is None:
            status = "new"
        elif existing.content_hash == content_hash:
            status = "unchanged"
        else:
            status = "changed"

        self._entries[normalized_path] = ManifestEntry(
            source_path=normalized_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            modified_time=modified_time,
            last_ingested=ingested_at,
        )

        return status

    def remove_entry(self, source_path: str) -> bool:
        """Remove entry from manifest.

        Args:
            source_path: Path to remove (will be normalized).

        Returns:
            True if entry existed and was removed.
        """
        normalized = self.normalize_path(source_path)
        if normalized in self._entries:
            del self._entries[normalized]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def get_all_entries(self) -> list[ManifestEntry]:
        """Get all manifest entries."""
        return list(self._entries.values())

    def normalize_path(self, path: Path | str) -> str:
        """Normalize path for manifest storage using canonical resolution.

        Resolves symlinks and normalizes path separators to ensure equivalent
        paths (e.g., docs/file.md vs sub/../docs/file.md) map to the same key.

        Args:
            path: Path to normalize.

        Returns:
            Canonical path string with forward slashes.
        """
        p = Path(path)
        # Resolve to canonical absolute path (resolves symlinks, .., etc.)
        try:
            resolved = p.resolve()
        except (OSError, ValueError):
            # If resolution fails (e.g., non-existent path), normalize anyway
            resolved = p
        # Make relative if possible, otherwise use absolute
        try:
            rel_path = resolved.relative_to(Path.cwd().resolve())
        except ValueError:
            rel_path = resolved
        return str(rel_path).replace("\\", "/")
