"""Deterministic vault manifest generation.

Produces a JSON manifest that records every adapted note and its
adaptation metadata for future auditability.
"""

import json
from datetime import datetime, timezone

from tracevault.wiki.vault.models import VaultNotePlan

VAULT_MANIFEST_VERSION = "vault-manifest-v1"


def build_vault_manifest(
    wiki_dir: str,
    vault_dir: str,
    note_plans: list[VaultNotePlan],
) -> dict:
    """Build a deterministic vault manifest dictionary.

    The manifest records:
    - generation timestamp
    - source wiki directory
    - target vault directory
    - per-note adaptation mapping (source, destination, identity)
    """
    accepted = [n for n in note_plans if not n.rejected and not n.skipped]

    return {
        "version": VAULT_MANIFEST_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_wiki_dir": wiki_dir,
        "vault_dir": vault_dir,
        "total_notes": len(accepted),
        "notes": [
            {
                "source_relative": n.relative_source,
                "destination_relative": n.relative_destination,
                "original_filename": n.original_filename,
                "note_id": n.note_id,
                "note_type": n.note_type,
                "status": n.status,
                "evidence_count": n.evidence_count,
            }
            for n in sorted(accepted, key=lambda x: x.relative_destination)
        ],
    }


def render_vault_manifest(
    wiki_dir: str,
    vault_dir: str,
    note_plans: list[VaultNotePlan],
) -> str:
    """Return the manifest as a JSON string."""
    return json.dumps(
        build_vault_manifest(wiki_dir, vault_dir, note_plans),
        indent=2,
        sort_keys=False,
    )
