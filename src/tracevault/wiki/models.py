"""Data models for wiki export.

Defines structured types for wiki notes, claims, evidence references,
export metadata, and export results.

Key concepts:
- WikiNote: A complete wiki note with claims and evidence references
- WikiClaim: A statement backed (or not) by evidence references
- WikiEvidenceReference: Pointer to a source evidence item
- WikiSourceDocument: Structured source document reference for proof chain
- WikiSourceChunk: Structured source chunk reference for proof chain
- WikiExportMetadata: TraceVault metadata embedded in every exported note
- WikiExportResult: Output of a single-note export operation
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

ValidationStatus = Literal["validated", "validation_required"]


@dataclass
class WikiEvidenceReference:
    """Pointer to a source evidence item.

    Attributes:
        label: Display label (e.g., "E1")
        document_id: Source document identifier
        chunk_id: Source chunk identifier
        source_path: Original file path
        source_raw_hash: SHA-256 of the source document raw text
        raw_text_hash: SHA-256 of source raw text
        evidence_text_hash: Stable hash of the evidence excerpt text
        excerpt: Evidence text excerpt for the reference section
    """

    label: str
    document_id: str
    chunk_id: str
    source_path: str = ""
    source_raw_hash: str = ""
    raw_text_hash: str = ""
    evidence_text_hash: str = ""
    excerpt: str = ""

    def identity_key(self) -> tuple:
        """Return a stable identity tuple for deduplication.

        Identity is anchored on source location, not presentation label
        or optional metadata completeness.

        Priority:
        1. (chunk, document_id, chunk_id) — primary stable identity
        2. (document-evidence, document_id, evidence_text_hash)
        3. (document-source, document_id, source_raw_hash)
        4. (label-excerpt, label, excerpt) — conservative fallback
        """
        if self.document_id and self.chunk_id:
            return ("chunk", self.document_id, self.chunk_id)
        if self.document_id and self.evidence_text_hash:
            return ("document-evidence", self.document_id, self.evidence_text_hash)
        if self.document_id and self.source_raw_hash:
            return ("document-source", self.document_id, self.source_raw_hash)
        return (
            "label-excerpt",
            self.label,
            self.excerpt,
        )

    def has_required_label(self) -> bool:
        """Return True when the label is a non-empty, non-whitespace string."""
        return bool(
            isinstance(self.label, str)
            and self.label.strip()
        )

    def has_required_source_identity(self) -> bool:
        """Return True when both document_id and chunk_id are present.

        Missing means None, empty string, or whitespace-only string.
        This is the minimum identity required for strict-export
        proof-chain traceability.
        """
        return bool(
            isinstance(self.document_id, str)
            and self.document_id.strip()
            and isinstance(self.chunk_id, str)
            and self.chunk_id.strip()
        )

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "source_path": self.source_path,
            "source_raw_hash": self.source_raw_hash,
            "raw_text_hash": self.raw_text_hash,
            "evidence_text_hash": self.evidence_text_hash,
            "excerpt": self.excerpt,
        }


@dataclass
class WikiClaim:
    """A statement backed (or not) by evidence references.

    Attributes:
        statement: The claim text
        evidence_refs: Evidence references supporting this claim
        unsupported: Whether this claim lacks evidence support
    """

    statement: str
    evidence_refs: list[WikiEvidenceReference] = field(default_factory=list)
    unsupported: bool = False

    @property
    def has_evidence(self) -> bool:
        """Return True if this claim has at least one evidence reference."""
        return len(self.evidence_refs) > 0

    @property
    def is_supported(self) -> bool:
        """Return True if this claim is properly backed by evidence.

        A claim is supported when it is not marked unsupported and
        has at least one evidence reference.
        """
        return not self.unsupported and self.has_evidence

    def evidence_refs_missing_source_identity(self) -> list[WikiEvidenceReference]:
        """Return evidence refs that lack document_id or chunk_id.

        A ref is considered missing source identity when either field
        is None, empty, or whitespace-only.
        """
        return [
            ref for ref in self.evidence_refs
            if not ref.has_required_source_identity()
        ]

    def evidence_refs_missing_label(self) -> list[WikiEvidenceReference]:
        """Return evidence refs that lack a non-empty label.

        A ref is considered missing a label when the label is None,
        empty, or whitespace-only.
        """
        return [
            ref for ref in self.evidence_refs
            if not ref.has_required_label()
        ]

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "unsupported": self.unsupported,
        }


@dataclass
class WikiSourceDocument:
    """Structured source document reference for proof chain.

    Attributes:
        document_id: Source document identifier
        source_path: Original file path
        source_raw_hash: SHA-256 of the source document raw text
        content_hash: Content hash from ingestion layer
    """

    document_id: str
    source_path: str = ""
    source_raw_hash: str = ""
    content_hash: str = ""


@dataclass
class WikiSourceChunk:
    """Structured source chunk reference for proof chain.

    Attributes:
        document_id: Parent document identifier
        chunk_id: Chunk identifier
        source_raw_hash: SHA-256 of the source document raw text
        raw_text_hash: SHA-256 of the chunk raw text
        cleaned_text_hash: SHA-256 of the chunk cleaned text
        evidence_text_hash: Stable hash of the evidence excerpt text
    """

    document_id: str
    chunk_id: str
    source_raw_hash: str = ""
    raw_text_hash: str = ""
    cleaned_text_hash: str = ""
    evidence_text_hash: str = ""


@dataclass
class WikiExportMetadata:
    """TraceVault metadata embedded in every exported note.

    Preserves machine-readable proof-chain fields for future Phase 6B
    validation checks.

    Attributes:
        note_id: Unique note identifier
        note_type: Artifact type identifier
        status: Export status ("proposal" for proposal-first export)
        generated_at: UTC datetime when the note was generated
        generated_by: Generator tool identifier
        generator_version: TraceVault package version
        schema_version: Wiki export schema version
        source_policy: Which text field is authoritative
        validation_status: Whether the note passed validation
        confidence: Confidence level string
        evidence_count: Number of evidence items referenced
        source_documents: Structured source document references
        source_chunks: Structured source chunk references
    """

    note_id: str
    note_type: str = "compiled_knowledge_wiki_note"
    status: str = "proposal"
    generated_at: datetime | str = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    generated_by: str = "tracevault"
    generator_version: str = "0.1.0"
    schema_version: str = "wiki-export-v1"
    source_policy: str = "raw_text_authoritative"
    validation_status: ValidationStatus = "validation_required"
    confidence: str = ""
    evidence_count: int = 0
    source_documents: list[WikiSourceDocument] = field(default_factory=list)
    source_chunks: list[WikiSourceChunk] = field(default_factory=list)

    def generated_at_iso(self) -> str:
        """Return generated_at as an ISO 8601 UTC-normalized string.

        - timezone-aware datetime: converted to UTC via astimezone().
        - naive datetime: treated as UTC.
        - ISO string: parsed, converted to UTC if offset present.
        - Z-suffix strings: normalized to +00:00 for fromisoformat compat.
        - Invalid strings: raise ValueError (fail-closed).
        """
        if isinstance(self.generated_at, datetime):
            dt = self.generated_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat()

        s = self.generated_at
        # Normalize Z suffix to +00:00 for fromisoformat compatibility
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "note_type": self.note_type,
            "status": self.status,
            "generated_at": self.generated_at_iso(),
            "generated_by": self.generated_by,
            "generator_version": self.generator_version,
            "schema_version": self.schema_version,
            "source_policy": self.source_policy,
            "validation_status": self.validation_status,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "source_documents": [
                {
                    "document_id": d.document_id,
                    "source_path": d.source_path,
                    "source_raw_hash": d.source_raw_hash,
                    "content_hash": d.content_hash,
                }
                for d in self.source_documents
            ],
            "source_chunks": [
                {
                    "document_id": c.document_id,
                    "chunk_id": c.chunk_id,
                    "source_raw_hash": c.source_raw_hash,
                    "raw_text_hash": c.raw_text_hash,
                    "cleaned_text_hash": c.cleaned_text_hash,
                    "evidence_text_hash": c.evidence_text_hash,
                }
                for c in self.source_chunks
            ],
        }


@dataclass
class WikiNote:
    """A complete wiki note with claims and evidence references.

    A wiki note is a derived knowledge artifact, not a source of truth.

    Attributes:
        note_id: Unique note identifier
        title: Human-readable note title
        summary: Optional summary paragraph
        claims: Ordered list of claims with evidence references
        source_evidence: Raw evidence references (not tied to specific claims)
        metadata: WikiExportMetadata for traceability
    """

    note_id: str
    title: str
    summary: str = ""
    claims: list[WikiClaim] = field(default_factory=list)
    source_evidence: list[WikiEvidenceReference] = field(default_factory=list)
    metadata: WikiExportMetadata | None = None

    def unsupported_claims(self) -> list[WikiClaim]:
        """Return claims explicitly marked as unsupported."""
        return [c for c in self.claims if c.unsupported]

    def invalid_supported_claims(self) -> list[WikiClaim]:
        """Return claims marked supported (unsupported=False) but with no evidence.

        These claims violate the evidence contract: they claim to be
        supported but have no evidence_refs.
        """
        return [
            c for c in self.claims
            if not c.unsupported and not c.has_evidence
        ]

    def validate_claim_coverage(self) -> list[str]:
        """Validate that every supported claim has evidence.

        Returns a list of error messages. Empty list means valid.
        """
        errors: list[str] = []
        for claim in self.invalid_supported_claims():
            errors.append(
                f"Claim '{claim.statement}' is supported but has no evidence refs"
            )
        return errors

    def validate_evidence_source_identity(self) -> list[str]:
        """Validate that every supported claim evidence ref has document/chunk identity.

        Returns a list of error messages. Empty list means valid.
        Each error message identifies the claim statement, evidence label,
        and the missing fields so the upstream builder can debug the gap.
        """
        errors: list[str] = []
        for claim in self.claims:
            if claim.unsupported:
                continue
            for ref in claim.evidence_refs_missing_source_identity():
                errors.append(
                    f"evidence ref missing required source identity: "
                    f"claim='{claim.statement}', label='{ref.label}', "
                    f"document_id='{ref.document_id}', chunk_id='{ref.chunk_id}'"
                )
        return errors

    def validate_evidence_labels(self) -> list[str]:
        """Validate that every supported claim evidence ref has a non-empty label.

        Returns a list of error messages. Empty list means valid.
        A label is considered missing when it is None, empty, or whitespace-only.
        """
        errors: list[str] = []
        for claim in self.claims:
            if claim.unsupported:
                continue
            for ref in claim.evidence_refs_missing_label():
                errors.append(
                    f"evidence ref missing required label: "
                    f"claim='{claim.statement}', "
                    f"document_id='{ref.document_id}', chunk_id='{ref.chunk_id}'"
                )
        return errors

    def validate(self) -> list[str]:
        """Validate a WikiNote for export readiness.

        Checks structural identity consistency, claim coverage, evidence
        source identity, and evidence labels.
        Returns a list of error messages. Empty list means valid.

        Identity rule:
        - note.note_id must match note.metadata.note_id when metadata is
          present. Auto-correction is intentionally not performed; strict
          export should fail closed to surface upstream proof-chain errors.
        """
        errors: list[str] = []

        # Identity consistency: note_id must match metadata.note_id
        if self.metadata is not None and self.metadata.note_id != self.note_id:
            errors.append(
                f"note_id mismatch: note.note_id '{self.note_id}' does not "
                f"match metadata.note_id '{self.metadata.note_id}'"
            )

        errors.extend(self.validate_claim_coverage())
        errors.extend(self.validate_evidence_source_identity())
        errors.extend(self.validate_evidence_labels())
        return errors

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "summary": self.summary,
            "claims": [c.to_dict() for c in self.claims],
            "source_evidence": [e.to_dict() for e in self.source_evidence],
            "metadata": self.metadata.to_dict() if self.metadata else None,
        }


@dataclass
class WikiExportResult:
    """Output of a single-note export operation.

    Attributes:
        note_id: The exported note's identifier
        file_path: Target file path
        markdown: Rendered Markdown content (empty if rejected)
        written: Whether the file was written to disk
        skipped: Whether the file was skipped (already exists, no overwrite)
        rejected: Whether the export was blocked by contract validation
        reason: Human-readable reason for skip or rejection
    """

    note_id: str
    file_path: str
    markdown: str = ""
    written: bool = False
    skipped: bool = False
    rejected: bool = False
    reason: str = ""
