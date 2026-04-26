"""Ingestion module.

Provides document ingestion with differential ingest detection.

Components:
- models: DocumentRecord, IngestResult, IngestSummary
- hashing: SHA-256 content hashing
- loader: UTF-8 file loading with raw preservation
- manifest: JSON-based ingest state tracking
- pipeline: File and directory ingestion
"""

from tracevault.ingestion.hashing import compute_content_hash, compute_file_hash, verify_hash
from tracevault.ingestion.loader import (
    SUPPORTED_EXTENSIONS,
    get_source_type,
    is_supported_file,
    load_file,
)
from tracevault.ingestion.manifest import DEFAULT_MANIFEST_PATH, IngestManifest
from tracevault.ingestion.models import (
    DocumentRecord,
    DocumentStatus,
    IngestResult,
    IngestSummary,
    ManifestEntry,
)
from tracevault.ingestion.pipeline import (
    ingest_directory,
    ingest_file,
    ingest_path,
)

__all__ = [
    # Models
    "DocumentRecord",
    "DocumentStatus",
    "IngestResult",
    "IngestSummary",
    "ManifestEntry",
    # Hashing
    "compute_content_hash",
    "compute_file_hash",
    "verify_hash",
    # Loader
    "SUPPORTED_EXTENSIONS",
    "get_source_type",
    "is_supported_file",
    "load_file",
    # Manifest
    "IngestManifest",
    "DEFAULT_MANIFEST_PATH",
    # Pipeline
    "ingest_file",
    "ingest_directory",
    "ingest_path",
]
