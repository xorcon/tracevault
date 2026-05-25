"""Data models for Obsidian vault adaptation.

Defines structured types for the vault adapter plan, configuration,
and result.  The adapter is plan-first: it builds an inspectable
plan before touching the filesystem.
"""

from dataclasses import dataclass, field
from typing import Literal

VaultLayoutStrategy = Literal["default"]


@dataclass
class VaultAdapterConfig:
    """Runtime configuration for vault adaptation.

    Attributes:
        layout_strategy: Which layout strategy to use (currently only
            "default" is supported).
        allow_overwrite: If True, overwrite existing destination files.
        allow_unhealthy: If True, skip the Phase 6B health preflight
            gate and adapt notes even when they have errors.  Intended
            for test fixtures only.
        generate_index: If True (default), generate deterministic index
            notes (Home.md, By-Type.md, By-Source.md).
    """

    layout_strategy: VaultLayoutStrategy = "default"
    allow_overwrite: bool = False
    allow_unhealthy: bool = False
    generate_index: bool = True


@dataclass
class VaultNotePlan:
    """Planned adaptation for a single wiki note.

    Attributes:
        source_path: Absolute path to the source Phase 6A Markdown note.
        relative_source: Path relative to the exported wiki directory.
        destination_path: Absolute destination path in the vault.
        relative_destination: Path relative to the vault root.
        original_filename: Original Phase 6A filename (preserved).
        title: Note title parsed from Markdown body.
        note_id: note_id from YAML frontmatter.
        note_type: note_type from YAML frontmatter.
        status: status from YAML frontmatter.
        evidence_count: evidence_count parsed from frontmatter.
        source_document_ids: document_ids collected from frontmatter.
        rejected: True if the note should be excluded from adaptation.
        rejection_reason: Human-readable rejection reason.
        collision: True if rejected due to intra-plan destination collision.
        skipped: True if destination exists and overwrite not allowed.
    """

    source_path: str
    relative_source: str
    destination_path: str
    relative_destination: str
    original_filename: str
    title: str = ""
    note_id: str = ""
    note_type: str = ""
    status: str = ""
    evidence_count: int = 0
    source_document_ids: list[str] = field(default_factory=list)
    rejected: bool = False
    rejection_reason: str = ""
    collision: bool = False
    skipped: bool = False


@dataclass
class VaultIndexPlan:
    """Planned generation of a deterministic index note.

    Attributes:
        destination_path: Absolute destination path in the vault.
        relative_destination: Path relative to the vault root.
        filename: Index note filename (e.g., "Home.md").
        num_entries: Number of note entries the index will contain.
    """

    destination_path: str
    relative_destination: str
    filename: str
    num_entries: int = 0


@dataclass
class VaultAdaptationPlan:
    """Full plan for adapting wiki notes to an Obsidian vault structure.

    Built before any file is written.  Inspectable via the CLI
    ``wiki-vault-plan`` command.

    Attributes:
        wiki_dir: Source wiki directory path.
        vault_dir: Target vault directory path.
        notes: Per-note adaptation plans.
        index_notes: Planned index note files.
        manifest_path: Destination of the vault manifest JSON file.
        manifest_relative: Manifest path relative to vault root.
        health_errors: Number of Phase 6B health errors (preflight).
        health_warnings: Number of Phase 6B health warnings (preflight).
        health_passed: Whether the Phase 6B preflight check passed.
        config: The VaultAdapterConfig used to build this plan.
    """

    wiki_dir: str
    vault_dir: str
    notes: list[VaultNotePlan] = field(default_factory=list)
    index_notes: list[VaultIndexPlan] = field(default_factory=list)
    manifest_path: str = ""
    manifest_relative: str = ""
    health_errors: int = 0
    health_warnings: int = 0
    health_passed: bool = True
    config: VaultAdapterConfig | None = None

    @property
    def total_notes(self) -> int:
        return len(self.notes)

    @property
    def accepted_notes(self) -> list[VaultNotePlan]:
        return [n for n in self.notes if not n.rejected and not n.skipped]

    @property
    def rejected_notes(self) -> list[VaultNotePlan]:
        return [n for n in self.notes if n.rejected]

    @property
    def skipped_notes(self) -> list[VaultNotePlan]:
        return [n for n in self.notes if n.skipped]

    @property
    def collision_notes(self) -> list[VaultNotePlan]:
        return [n for n in self.notes if n.collision]

    def to_dict(self) -> dict:
        return {
            "wiki_dir": self.wiki_dir,
            "vault_dir": self.vault_dir,
            "health_passed": self.health_passed,
            "health_errors": self.health_errors,
            "health_warnings": self.health_warnings,
            "total_notes": self.total_notes,
            "accepted": len(self.accepted_notes),
            "rejected": len(self.rejected_notes),
            "collisions": len(self.collision_notes),
            "skipped": len(self.skipped_notes),
            "index_notes": [
                {
                    "filename": idx.filename,
                    "relative_destination": idx.relative_destination,
                    "num_entries": idx.num_entries,
                }
                for idx in self.index_notes
            ],
            "manifest_relative": self.manifest_relative,
            "notes": [
                {
                    "relative_source": n.relative_source,
                    "relative_destination": n.relative_destination,
                    "original_filename": n.original_filename,
                    "title": n.title,
                    "note_id": n.note_id,
                    "note_type": n.note_type,
                    "status": n.status,
                    "evidence_count": n.evidence_count,
                    "rejected": n.rejected,
                    "rejection_reason": n.rejection_reason,
                    "collision": n.collision,
                    "skipped": n.skipped,
                }
                for n in self.notes
            ],
        }


@dataclass
class VaultAdaptationResult:
    """Outcome of applying a vault adaptation plan.

    Attributes:
        plan: The plan that was applied.
        notes_copied: Number of notes successfully copied.
        notes_skipped: Number of notes skipped (already exists, no overwrite).
        notes_rejected: Number of notes rejected by the plan.
        index_notes_written: Number of index notes generated.
        manifest_written: Whether the manifest was written.
        errors: Non-fatal errors encountered during apply.
    """

    plan: VaultAdaptationPlan
    notes_copied: int = 0
    notes_skipped: int = 0
    notes_rejected: int = 0
    index_notes_written: int = 0
    manifest_written: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "wiki_dir": self.plan.wiki_dir,
            "vault_dir": self.plan.vault_dir,
            "notes_copied": self.notes_copied,
            "notes_skipped": self.notes_skipped,
            "notes_rejected": self.notes_rejected,
            "index_notes_written": self.index_notes_written,
            "manifest_written": self.manifest_written,
            "errors": self.errors,
            "success": self.success,
        }
