"""Obsidian vault adapter for TraceVault wiki notes.

Phase 6C — Optional Obsidian Vault Adapter

Organizes already-exported Phase 6A Markdown wiki notes into an
Obsidian-friendly vault structure while preserving TraceVault
metadata and proof-chain guarantees.
"""

from tracevault.wiki.vault.adapter import (
    adapt_to_obsidian_vault,
    apply_vault_plan,
    build_vault_plan,
)
from tracevault.wiki.vault.index import (
    render_by_source_index,
    render_by_type_index,
    render_home_index,
    render_index_note,
)
from tracevault.wiki.vault.manifest import (
    build_vault_manifest,
    render_vault_manifest,
)
from tracevault.wiki.vault.models import (
    VaultAdaptationPlan,
    VaultAdaptationResult,
    VaultAdapterConfig,
    VaultIndexPlan,
    VaultNotePlan,
)

__all__ = [
    # Configuration
    "VaultAdapterConfig",
    # Plan models
    "VaultNotePlan",
    "VaultIndexPlan",
    "VaultAdaptationPlan",
    # Result
    "VaultAdaptationResult",
    # Core API
    "build_vault_plan",
    "apply_vault_plan",
    "adapt_to_obsidian_vault",
    # Index rendering
    "render_home_index",
    "render_by_type_index",
    "render_by_source_index",
    "render_index_note",
    # Manifest
    "build_vault_manifest",
    "render_vault_manifest",
]
