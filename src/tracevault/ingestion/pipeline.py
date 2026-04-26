"""Ingestion pipeline.

Orchestrates file loading, hashing, and manifest management for differential ingest.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from tracevault.ingestion.hashing import compute_content_hash
from tracevault.ingestion.loader import (
    get_source_type,
    is_supported_file,
    load_file,
)
from tracevault.ingestion.manifest import DEFAULT_MANIFEST_PATH, IngestManifest
from tracevault.ingestion.models import (
    DocumentRecord,
    IngestResult,
    IngestSummary,
)

# Directories to ignore during directory traversal
IGNORED_DIRS = {
    ".git",
    ".tracevault",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "data",
    "storage",
    "uploads",
    "documents",
    "indexes",
    "vector_store",
    "vector-db",
    "chroma",
    "qdrant_storage",
    "lancedb",
}


def _get_modified_time(file_path: Path) -> str:
    """Get file modification time as ISO 8601 string."""
    mtime = file_path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt.isoformat()


def _get_ingested_at() -> str:
    """Get current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def ingest_file(
    file_path: Path,
    manifest: IngestManifest,
) -> IngestResult:
    """Ingest a single file.

    Args:
        file_path: Path to file.
        manifest: Manifest instance for tracking.

    Returns:
        IngestResult with status and document record if successful.
    """
    source_path = manifest.normalize_path(file_path)

    # Check if supported
    if not is_supported_file(file_path):
        return IngestResult(
            source_path=source_path,
            status="skipped",
            error=f"Unsupported file type: {file_path.suffix}",
        )

    try:
        # Load raw content
        content, size_bytes = load_file(file_path)

        # Compute hash
        content_hash = compute_content_hash(content)

        # Get timestamps
        modified_time = _get_modified_time(file_path)
        ingested_at = _get_ingested_at()

        # Update manifest and get status
        status = manifest.update_entry(
            source_path=source_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            modified_time=modified_time,
            ingested_at=ingested_at,
        )

        # Create document record
        document_id = DocumentRecord.generate_document_id(source_path, content_hash)
        record = DocumentRecord(
            document_id=document_id,
            source_path=source_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            modified_time=modified_time,
            ingested_at=ingested_at,
            source_type=get_source_type(file_path),
        )

        return IngestResult(
            source_path=source_path,
            status=status,
            document_record=record,
        )

    except FileNotFoundError as e:
        return IngestResult(
            source_path=source_path,
            status="error",
            error=f"File not found: {e}",
        )
    except PermissionError as e:
        return IngestResult(
            source_path=source_path,
            status="error",
            error=f"Permission denied: {e}",
        )
    except UnicodeDecodeError as e:
        return IngestResult(
            source_path=source_path,
            status="error",
            error=f"Encoding error: {e}",
        )
    except Exception as e:
        return IngestResult(
            source_path=source_path,
            status="error",
            error=f"Unexpected error: {e}",
        )


def ingest_directory(
    directory_path: Path,
    manifest: IngestManifest | None = None,
) -> IngestSummary:
    """Ingest all supported files in directory recursively.

    Args:
        directory_path: Directory to scan.
        manifest: Manifest instance. If None, uses default path.

    Returns:
        IngestSummary with counts and detailed results.
    """
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    if not directory_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory_path}")

    if manifest is None:
        manifest = IngestManifest(DEFAULT_MANIFEST_PATH)

    results: list[IngestResult] = []
    counts = {"new": 0, "unchanged": 0, "changed": 0, "skipped": 0, "error": 0}

    # Walk directory
    for root, dirs, files in os.walk(directory_path):
        root_path = Path(root)

        # Filter out ignored directories and hidden directories (modify in-place)
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS and not d.startswith(".")
        ]

        for filename in files:
            file_path = root_path / filename

            # Skip hidden files
            if filename.startswith("."):
                result = IngestResult(
                    source_path=manifest.normalize_path(file_path),
                    status="skipped",
                    error="Hidden file",
                )
            else:
                result = ingest_file(file_path, manifest)

            results.append(result)
            counts[result.status] = counts.get(result.status, 0) + 1

    # Save manifest
    manifest.save()

    return IngestSummary(
        total_files=len(results),
        new_count=counts["new"],
        unchanged_count=counts["unchanged"],
        changed_count=counts["changed"],
        skipped_count=counts["skipped"],
        error_count=counts["error"],
        results=results,
    )


def ingest_path(
    path: Path | str,
    manifest_path: Path | str | None = None,
) -> IngestSummary | IngestResult:
    """Ingest a file or directory.

    Args:
        path: Path to file or directory.
        manifest_path: Optional custom manifest path.

    Returns:
        IngestSummary for directories, IngestResult for files.
    """
    path = Path(path)

    if manifest_path is None:
        manifest_path = DEFAULT_MANIFEST_PATH

    manifest = IngestManifest(manifest_path)

    if path.is_file():
        result = ingest_file(path, manifest)
        manifest.save()
        return result

    if path.is_dir():
        return ingest_directory(path, manifest)

    raise FileNotFoundError(f"Path not found: {path}")
