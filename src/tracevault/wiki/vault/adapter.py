"""Core vault adaptation engine.

Plan-first, non-destructive Obsidian vault adapter.

Public API:
- build_vault_plan(...)    — build an inspectable adaptation plan
- apply_vault_plan(...)    — apply a plan to the filesystem
- adapt_to_obsidian_vault() — convenience one-liner (plan + apply)
"""

import shutil
from pathlib import Path

from tracevault.wiki.health import check_wiki_health
from tracevault.wiki.parser import parse_wiki_note
from tracevault.wiki.vault.index import (
    build_index_plans,
    render_index_note,
)
from tracevault.wiki.vault.layout import (
    resolve_index_dir,
    resolve_manifest_path,
    resolve_note_destination,
    resolve_notes_dir,
)
from tracevault.wiki.vault.manifest import render_vault_manifest
from tracevault.wiki.vault.models import (
    VaultAdaptationPlan,
    VaultAdaptationResult,
    VaultAdapterConfig,
    VaultNotePlan,
)


def _collect_wiki_md_files(wiki_dir: Path) -> list[Path]:
    """Collect .md files recursively, sorted for determinism.

    Skips hidden directories (starting with . or _).
    """
    files: list[Path] = []
    for child in sorted(wiki_dir.iterdir()):
        if child.is_dir():
            if child.name.startswith((".", "_")):
                continue
            files.extend(_collect_wiki_md_files(child))
        elif child.suffix.lower() == ".md":
            files.append(child)
    return files


def _parse_source_document_ids(parsed) -> list[str]:
    """Extract document_ids from frontmatter source_documents or body."""
    doc_ids: list[str] = []
    seen: set[str] = set()

    source_docs = parsed.frontmatter.get("source_documents")
    if isinstance(source_docs, list):
        for doc in source_docs:
            if isinstance(doc, dict):
                did = doc.get("document_id")
                if did and did not in seen:
                    doc_ids.append(str(did))
                    seen.add(did)

    # Fallback: scan body for Document: `doc_id` patterns
    if not doc_ids:
        import re
        for line in (parsed.body or "").split("\n"):
            m = re.search(r"\*\*Document\*\*:\s+`([^`]+)`", line)
            if m:
                did = m.group(1)
                if did and did not in seen:
                    doc_ids.append(did)
                    seen.add(did)

    return doc_ids


def _parse_note_title(body: str) -> str:
    """Extract the H1 title from the Markdown body."""
    for line in (body or "").split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _parse_evidence_count(fm: dict) -> int:
    """Extract evidence_count from frontmatter, defaulting to 0."""
    val = fm.get("evidence_count")
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def build_vault_plan(
    wiki_dir: Path | str,
    vault_dir: Path | str,
    config: VaultAdapterConfig | None = None,
) -> VaultAdaptationPlan:
    """Build an inspectable vault adaptation plan.

    This function:
    1. Runs a Phase 6B health preflight check on the wiki directory.
    2. Rejects all notes if health has errors (unless allow_unhealthy).
    3. Parses each note for metadata.
    4. Detects destination file collisions.
    5. Plans index note and manifest generation.

    Args:
        wiki_dir: Source directory with Phase 6A exported Markdown notes.
        vault_dir: Target Obsidian vault directory.
        config: Optional adapter configuration.

    Returns:
        VaultAdaptationPlan with all note plans and index plans.

    Raises:
        ValueError: If wiki_dir does not exist.
    """
    wiki_dir = Path(wiki_dir)
    vault_dir = Path(vault_dir)
    config = config or VaultAdapterConfig()

    if not wiki_dir.exists():
        raise ValueError(f"Wiki directory does not exist: {wiki_dir}")

    plan = VaultAdaptationPlan(
        wiki_dir=str(wiki_dir),
        vault_dir=str(vault_dir),
        config=config,
    )

    # --- Health preflight ---
    if not config.allow_unhealthy:
        report = check_wiki_health(wiki_dir)
        plan.health_errors = report.error_count
        plan.health_warnings = report.warning_count
        plan.health_passed = report.passed

        if not plan.health_passed:
            # Reject all notes with health error context
            md_files = _collect_wiki_md_files(wiki_dir)
            for fp in md_files:
                note_plan = VaultNotePlan(
                    source_path=str(fp),
                    relative_source=str(fp.relative_to(wiki_dir)),
                    destination_path=str(resolve_note_destination(
                        vault_dir, fp.name
                    )),
                    relative_destination=str(
                        resolve_note_destination(vault_dir, fp.name).relative_to(
                            vault_dir
                        )
                    ),
                    original_filename=fp.name,
                    rejected=True,
                    rejection_reason=(
                        f"Health preflight failed with {plan.health_errors} "
                        f"error(s). Use --allow-unhealthy to bypass."
                    ),
                )
                plan.notes.append(note_plan)

            plan.manifest_path = str(resolve_manifest_path(vault_dir))
            plan.manifest_relative = str(
                resolve_manifest_path(vault_dir).relative_to(vault_dir)
            )
            return plan

    # --- Parse and plan each note ---
    md_files = _collect_wiki_md_files(wiki_dir)

    for fp in md_files:
        dest = resolve_note_destination(vault_dir, fp.name)
        rel_dest = str(dest.relative_to(vault_dir))

        # Parse the note for metadata
        try:
            parsed = parse_wiki_note(fp)
        except Exception as exc:
            plan.notes.append(VaultNotePlan(
                source_path=str(fp),
                relative_source=str(fp.relative_to(wiki_dir)),
                destination_path=str(dest),
                relative_destination=rel_dest,
                original_filename=fp.name,
                rejected=True,
                rejection_reason=f"Failed to parse note: {exc}",
            ))
            continue

        title = _parse_note_title(parsed.body)
        fm = parsed.frontmatter
        note_id = str(fm.get("note_id", "")) if fm.get("note_id") else ""
        note_type = str(fm.get("note_type", "")) if fm.get("note_type") else ""
        status = str(fm.get("status", "")) if fm.get("status") else ""
        evidence_count = _parse_evidence_count(fm)
        source_doc_ids = _parse_source_document_ids(parsed)

        note_plan = VaultNotePlan(
            source_path=str(fp),
            relative_source=str(fp.relative_to(wiki_dir)),
            destination_path=str(dest),
            relative_destination=rel_dest,
            original_filename=fp.name,
            title=title,
            note_id=note_id,
            note_type=note_type,
            status=status,
            evidence_count=evidence_count,
            source_document_ids=source_doc_ids,
        )

        # Collision detection (destination already exists on disk)
        if dest.exists() and not config.allow_overwrite:
            note_plan.skipped = True

        plan.notes.append(note_plan)

    # --- Intra-plan collision detection ---
    seen_dest: dict[str, str] = {}
    for note_plan in plan.notes:
        if note_plan.rejected:
            continue
        dest = note_plan.destination_path
        if dest in seen_dest:
            note_plan.rejected = True
            note_plan.rejection_reason = (
                f"Duplicate destination '{dest}' (first claimed by "
                f"'{seen_dest[dest]}')"
            )
            note_plan.collision = True
        else:
            seen_dest[dest] = note_plan.relative_source

    # --- Pre-write source/destination validation ---
    for note_plan in plan.notes:
        if note_plan.rejected:
            continue
        src = Path(note_plan.source_path)
        dest = Path(note_plan.destination_path)
        if not src.is_file():
            note_plan.rejected = True
            note_plan.rejection_reason = "Source file not found"
        elif dest.exists() and not config.allow_overwrite:
            note_plan.skipped = True

    # Validate parent paths can be created (dry-run, no filesystem writes)
    for note_plan in plan.notes:
        if note_plan.rejected or note_plan.skipped:
            continue
        dest = Path(note_plan.destination_path)
        parent = dest.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not parent.exists() or not parent.is_dir():
            note_plan.rejected = True
            note_plan.rejection_reason = "Cannot create destination parent path"

    # --- Index plans ---
    if config.generate_index:
        plan.index_notes = build_index_plans(vault_dir, plan.notes)

    # --- Manifest ---
    plan.manifest_path = str(resolve_manifest_path(vault_dir))
    plan.manifest_relative = str(
        resolve_manifest_path(vault_dir).relative_to(vault_dir)
    )

    return plan


def apply_vault_plan(plan: VaultAdaptationPlan) -> VaultAdaptationResult:
    """Apply a vault adaptation plan to the filesystem.

    Copies note files, generates index notes, and writes the manifest.
    Does not create .obsidian/ directories.

    Args:
        plan: A VaultAdaptationPlan from build_vault_plan().

    Returns:
        VaultAdaptationResult with counts and any non-fatal errors.
    """
    vault_dir = Path(plan.vault_dir)
    config = plan.config or VaultAdapterConfig()

    result = VaultAdaptationResult(plan=plan)

    # === Validation phase (no filesystem writes) ===

    # (a) Validate health_passed
    if not plan.health_passed:
        result.errors.append(
            f"Health preflight failed with {plan.health_errors} error(s). "
            "Refusing to write any files."
        )
        return result

    # (b) Validate no rejected note plans
    if plan.rejected_notes:
        result.notes_rejected = len(plan.rejected_notes)
        result.errors.append(
            f"{len(plan.rejected_notes)} note(s) rejected by plan. "
            "Refusing to write any files."
        )
        return result

    # (c) Validate no duplicate destination paths (defensive)
    dest_check: dict[str, str] = {}
    for note_plan in plan.notes:
        if note_plan.rejected or note_plan.skipped:
            continue
        d = note_plan.destination_path
        if d in dest_check:
            result.errors.append(
                f"Duplicate destination '{d}' (claimed by "
                f"'{dest_check[d]}' and '{note_plan.relative_source}')"
            )
            return result
        dest_check[d] = note_plan.relative_source

    # (d) Validate source files are readable
    for note_plan in plan.notes:
        if note_plan.rejected or note_plan.skipped:
            continue
        if not Path(note_plan.source_path).is_file():
            result.errors.append(
                f"Source file not found: {note_plan.source_path}"
            )
            return result

    # (e) Validate parent paths can be created (dry-run)
    parents_to_check: set[Path] = set()
    for note_plan in plan.notes:
        if note_plan.rejected or note_plan.skipped:
            continue
        parents_to_check.add(Path(note_plan.destination_path).parent)
    for parent in parents_to_check:
        p = parent
        while not p.exists() and p != p.parent:
            p = p.parent
        if not p.exists() or not p.is_dir():
            result.errors.append(f"Cannot create parent path: {parent}")
            return result

    # === Write phase (only reached if all validation passes) ===

    # Create base directories
    try:
        resolve_notes_dir(vault_dir).mkdir(parents=True, exist_ok=True)
        if config.generate_index:
            resolve_index_dir(vault_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        result.errors.append(f"Failed to create vault directories: {exc}")
        return result

    # --- Copy notes (byte-preserving) ---
    for note_plan in plan.notes:
        if note_plan.rejected:
            result.notes_rejected += 1
            continue
        if note_plan.skipped:
            result.notes_skipped += 1
            continue

        src = Path(note_plan.source_path)
        dest = Path(note_plan.destination_path)

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest))
            result.notes_copied += 1
        except OSError as exc:
            result.errors.append(
                f"Failed to copy {note_plan.relative_source}: {exc}"
            )

    # --- Generate index notes ---
    if config.generate_index:
        for index_plan in plan.index_notes:
            dest = Path(index_plan.destination_path)
            try:
                content = render_index_note(
                    index_plan.filename, plan.notes
                )
                dest.write_text(content, encoding="utf-8")
                result.index_notes_written += 1
            except OSError as exc:
                result.errors.append(
                    f"Failed to write index {index_plan.filename}: {exc}"
                )

    # --- Write manifest ---
    try:
        manifest_content = render_vault_manifest(
            plan.wiki_dir, plan.vault_dir, plan.notes
        )
        manifest_path = Path(plan.manifest_path)
        manifest_path.write_text(manifest_content, encoding="utf-8")
        result.manifest_written = True
    except OSError as exc:
        result.errors.append(f"Failed to write manifest: {exc}")

    return result


def adapt_to_obsidian_vault(
    wiki_dir: Path | str,
    vault_dir: Path | str,
    config: VaultAdapterConfig | None = None,
) -> VaultAdaptationResult:
    """Convenience function: build plan and apply in one call.

    Args:
        wiki_dir: Source directory with Phase 6A exported Markdown notes.
        vault_dir: Target Obsidian vault directory.
        config: Optional adapter configuration.

    Returns:
        VaultAdaptationResult with counts and any non-fatal errors.
    """
    plan = build_vault_plan(wiki_dir, vault_dir, config=config)
    return apply_vault_plan(plan)
