"""Tests for Phase 6C — Optional Obsidian Vault Adapter.

Synthetic-only fixtures. No real private vault content.
Covers:
1. plan generation from valid exported notes
2. health preflight blocks unhealthy notes
3. content copied unchanged
4. YAML frontmatter preserved
5. deterministic destination mapping
6. collision detection
7. existing file skipped without overwrite
8. overwrite only when explicitly enabled
9. index generation deterministic and metadata-only
10. manifest generation deterministic
"""

import json
from pathlib import Path

import pytest

from tracevault.wiki.exporter import export_note
from tracevault.wiki.markdown import render_note
from tracevault.wiki.models import (
    WikiClaim,
    WikiEvidenceReference,
    WikiExportMetadata,
    WikiNote,
    WikiSourceChunk,
    WikiSourceDocument,
)
from tracevault.wiki.vault.adapter import (
    adapt_to_obsidian_vault,
    apply_vault_plan,
    build_vault_plan,
)
from tracevault.wiki.vault.index import (
    render_by_source_index,
    render_by_type_index,
    render_home_index,
)
from tracevault.wiki.vault.layout import (
    INDEX_SUBDIR,
    MANIFEST_FILENAME,
    NOTES_SUBDIR,
)
from tracevault.wiki.vault.manifest import build_vault_manifest
from tracevault.wiki.vault.models import (
    VaultAdaptationPlan,
    VaultAdapterConfig,
    VaultNotePlan,
)

GENERATED_AT = "2026-01-01T00:00:00+00:00"


def _make_validated_note(
    title="Test Note",
    note_id="note_001",
    doc_id="doc_001",
    chunk_id="chunk_001",
) -> WikiNote:
    """Create a fully validated WikiNote for synthetic fixtures."""
    ref = WikiEvidenceReference(
        label="E1", document_id=doc_id, chunk_id=chunk_id
    )
    doc = WikiSourceDocument(document_id=doc_id, source_raw_hash="abc123")
    chunk = WikiSourceChunk(
        document_id=doc_id,
        chunk_id=chunk_id,
        source_raw_hash="abc123",
        evidence_text_hash="def456",
    )
    meta = WikiExportMetadata(
        note_id=note_id,
        generated_at=GENERATED_AT,
        validation_status="validated",
        evidence_count=1,
        source_documents=[doc],
        source_chunks=[chunk],
    )
    return WikiNote(
        note_id=note_id,
        title=title,
        claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
        source_evidence=[ref],
        metadata=meta,
    )


def _write_validated_note_to_wiki(
    wiki_dir: Path,
    title="Test Note",
    note_id="note_001",
    doc_id="doc_001",
) -> str:
    """Export a validated note to wiki_dir and return the rendered Markdown."""
    note = _make_validated_note(title=title, note_id=note_id, doc_id=doc_id)
    export_note(note, wiki_dir, strict=False)
    return render_note(note)


def _write_synthetic_note(wiki_dir: Path, filename: str, content: str) -> None:
    """Write raw synthetic Markdown directly (bypasses exporter)."""
    (wiki_dir / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Plan generation from valid exported notes
# ---------------------------------------------------------------------------

class TestPlanGeneration:
    def test_plan_from_valid_notes(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, title="Alpha", note_id="note_a")
        _write_validated_note_to_wiki(
            wiki_dir, title="Beta", note_id="note_b", doc_id="doc_002"
        )

        plan = build_vault_plan(wiki_dir, vault_dir)

        assert plan.total_notes == 2
        assert len(plan.accepted_notes) == 2
        assert not plan.rejected_notes
        assert plan.health_passed is True
        assert plan.manifest_relative == MANIFEST_FILENAME

    def test_plan_health_passed(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        plan = build_vault_plan(wiki_dir, vault_dir)
        assert plan.health_passed is True
        assert plan.health_errors == 0

    def test_plan_preserves_note_metadata(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(
            wiki_dir, title="Governance", note_id="gov_001", doc_id="doc_gov"
        )

        plan = build_vault_plan(wiki_dir, vault_dir)
        note = plan.notes[0]
        assert note.title == "Governance"
        assert note.note_id == "gov_001"
        assert note.note_type == "compiled_knowledge_wiki_note"
        assert note.evidence_count == 1
        assert "doc_gov" in note.source_document_ids

    def test_plan_raises_for_missing_wiki_dir(self, tmp_path: Path):
        with pytest.raises(ValueError, match="does not exist"):
            build_vault_plan(tmp_path / "nope", tmp_path / "vault")


# ---------------------------------------------------------------------------
# 2. Health preflight blocks unhealthy notes
# ---------------------------------------------------------------------------

class TestHealthPreflight:
    def test_health_errors_block_plan(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        # Write a note with no frontmatter — health error
        _write_synthetic_note(
            wiki_dir, "bad.md", "# No Frontmatter\nNo YAML.\n"
        )

        plan = build_vault_plan(wiki_dir, vault_dir)

        assert plan.health_passed is False
        assert plan.health_errors > 0
        assert all(n.rejected for n in plan.notes)

    def test_allow_unhealthy_bypasses_preflight(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_synthetic_note(
            wiki_dir, "bad.md", "# No Frontmatter\nNo YAML.\n"
        )

        config = VaultAdapterConfig(allow_unhealthy=True)
        plan = build_vault_plan(wiki_dir, vault_dir, config=config)

        assert plan.health_passed is True  # not run
        assert plan.health_errors == 0
        # Note is not rejected by health gate (may be rejected by parse)
        assert not all(n.rejected for n in plan.notes)


# ---------------------------------------------------------------------------
# 3. Content copied unchanged
# ---------------------------------------------------------------------------

class TestContentPreservation:
    def test_content_copied_unchanged(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        original_md = _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)

        assert result.notes_copied == 1
        # Find the copied file
        copied = (vault_dir / NOTES_SUBDIR).glob("*.md")
        copied_content = next(copied).read_text(encoding="utf-8")
        assert copied_content == original_md

    def test_evidence_section_preserved(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(
            wiki_dir, title="Evidence Test", doc_id="doc_ev"
        )

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.notes_copied == 1
        copied = (vault_dir / NOTES_SUBDIR).glob("*.md")
        content = next(copied).read_text(encoding="utf-8")
        assert "## Evidence References" in content
        assert "**Document**: `doc_ev`" in content


# ---------------------------------------------------------------------------
# 4. YAML frontmatter preserved
# ---------------------------------------------------------------------------

class TestFrontmatterPreservation:
    def test_yaml_frontmatter_preserved(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.notes_copied == 1
        copied = (vault_dir / NOTES_SUBDIR).glob("*.md")
        content = next(copied).read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert 'note_id: "note_001"' in content
        assert 'note_type: "compiled_knowledge_wiki_note"' in content
        assert "evidence_count: 1" in content

    def test_tracevault_metadata_section_preserved(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.notes_copied == 1
        copied = (vault_dir / NOTES_SUBDIR).glob("*.md")
        content = next(copied).read_text(encoding="utf-8")
        assert "## TraceVault Metadata" in content
        assert "note_id:" in content


# ---------------------------------------------------------------------------
# 5. Deterministic destination mapping
# ---------------------------------------------------------------------------

class TestDeterministicDestination:
    def test_note_goes_to_TraceVault_Notes(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, note_id="note_det")

        plan = build_vault_plan(wiki_dir, vault_dir)
        note = plan.notes[0]
        assert note.relative_destination.startswith(NOTES_SUBDIR + "/")
        assert note.original_filename == note.relative_destination.split("/")[-1]

    def test_same_note_same_destination(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        plan1 = build_vault_plan(wiki_dir, vault_dir)
        plan2 = build_vault_plan(wiki_dir, vault_dir)
        assert plan1.notes[0].destination_path == plan2.notes[0].destination_path

    def test_original_filename_preserved(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, title="AI Governance", note_id="note_001")

        plan = build_vault_plan(wiki_dir, vault_dir)
        # The original Phase 6A filename should be preserved
        assert "ai-governance" in plan.notes[0].original_filename
        # The hex-encoded note_id is part of the filename
        assert "6e6f74655f303031" in plan.notes[0].original_filename


# ---------------------------------------------------------------------------
# 6. Collision detection
# ---------------------------------------------------------------------------

class TestCollisionDetection:
    def test_existing_file_detected_as_collision(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        vault_dir.mkdir()

        _write_validated_note_to_wiki(wiki_dir)

        # Pre-create the destination file
        plan = build_vault_plan(wiki_dir, vault_dir)
        dest = Path(plan.notes[0].destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre-existing content")

        # Rebuild plan — destination now exists
        plan2 = build_vault_plan(wiki_dir, vault_dir)
        assert plan2.notes[0].skipped is True


# ---------------------------------------------------------------------------
# 7. Existing file skipped without overwrite
# ---------------------------------------------------------------------------

class TestSkipWithoutOverwrite:
    def test_skipped_without_overwrite(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        vault_dir.mkdir()

        _write_validated_note_to_wiki(wiki_dir)

        # Pre-create destination
        plan = build_vault_plan(wiki_dir, vault_dir)
        dest = Path(plan.notes[0].destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre-existing content")

        # Adapt without overwrite
        plan2 = build_vault_plan(wiki_dir, vault_dir)
        result = apply_vault_plan(plan2)

        assert result.notes_skipped == 1
        assert result.notes_copied == 0
        # Original content preserved
        assert dest.read_text() == "pre-existing content"


# ---------------------------------------------------------------------------
# 8. Overwrite only when explicitly enabled
# ---------------------------------------------------------------------------

class TestOverwriteOnlyWhenEnabled:
    def test_overwrite_with_flag(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        vault_dir.mkdir()

        _write_validated_note_to_wiki(wiki_dir)

        # Pre-create destination
        plan = build_vault_plan(wiki_dir, vault_dir)
        dest = Path(plan.notes[0].destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre-existing content")

        # Adapt WITH overwrite
        config = VaultAdapterConfig(allow_overwrite=True)
        plan2 = build_vault_plan(wiki_dir, vault_dir, config=config)
        result = apply_vault_plan(plan2)

        assert result.notes_copied == 1
        assert result.notes_skipped == 0
        # Content should be the wiki content, not the pre-existing
        assert dest.read_text() != "pre-existing content"

    def test_no_overwrite_default(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        vault_dir.mkdir()

        _write_validated_note_to_wiki(wiki_dir)

        # Pre-create destination
        plan = build_vault_plan(wiki_dir, vault_dir)
        dest = Path(plan.notes[0].destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre-existing")

        # Default config — no overwrite
        plan2 = build_vault_plan(wiki_dir, vault_dir)
        result = apply_vault_plan(plan2)

        assert result.notes_skipped == 1


# ---------------------------------------------------------------------------
# 9. Index generation deterministic and metadata-only
# ---------------------------------------------------------------------------

class TestIndexGeneration:
    def test_home_index_rendered(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, title="Alpha", note_id="note_a")
        _write_validated_note_to_wiki(wiki_dir, title="Beta", note_id="note_b")

        plan = build_vault_plan(wiki_dir, vault_dir)
        result = apply_vault_plan(plan)

        assert result.index_notes_written == 3
        home = vault_dir / INDEX_SUBDIR / "Home.md"
        assert home.exists()
        content = home.read_text(encoding="utf-8")
        assert "# TraceVault Home" in content
        assert "[[" in content  # wikilink syntax
        assert "]]" in content

    def test_by_type_index_rendered(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, title="Alpha", note_id="note_a")

        plan = build_vault_plan(wiki_dir, vault_dir)
        result = apply_vault_plan(plan)
        assert result.index_notes_written >= 1

        by_type = vault_dir / INDEX_SUBDIR / "By-Type.md"
        assert by_type.exists()
        content = by_type.read_text(encoding="utf-8")
        assert "## compiled_knowledge_wiki_note" in content

    def test_by_source_index_rendered(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, doc_id="doc_alpha")

        plan = build_vault_plan(wiki_dir, vault_dir)
        result = apply_vault_plan(plan)
        assert result.index_notes_written >= 1

        by_source = vault_dir / INDEX_SUBDIR / "By-Source.md"
        assert by_source.exists()
        content = by_source.read_text(encoding="utf-8")
        assert "## doc_alpha" in content

    def test_index_deterministic(self, tmp_path: Path):
        """Rendering twice produces identical output."""
        note_plans = [
            VaultNotePlan(
                source_path="/wiki/a.md",
                relative_source="a.md",
                destination_path="/vault/TraceVault/Notes/a.md",
                relative_destination="TraceVault/Notes/a.md",
                original_filename="a.md",
                title="Alpha",
                note_id="note_a",
                note_type="compiled_knowledge_wiki_note",
                status="published",
                evidence_count=2,
                source_document_ids=["doc_1"],
            ),
        ]
        r1 = render_home_index(note_plans)
        r2 = render_home_index(note_plans)
        assert r1 == r2

    def test_index_no_llm_generated_content(self, tmp_path: Path):
        """Index notes must not contain summarized or inferred content."""
        note_plans = [
            VaultNotePlan(
                source_path="/wiki/a.md",
                relative_source="a.md",
                destination_path="/vault/TraceVault/Notes/a.md",
                relative_destination="TraceVault/Notes/a.md",
                original_filename="a.md",
                title="Alpha",
                note_id="note_a",
                note_type="compiled_knowledge_wiki_note",
                status="published",
                evidence_count=2,
                source_document_ids=["doc_1"],
            ),
        ]
        home = render_home_index(note_plans)
        by_type = render_by_type_index(note_plans)
        by_source = render_by_source_index(note_plans)

        # Should not contain summarization language
        for content in (home, by_type, by_source):
            for phrase in (
                "in summary",
                "this note discusses",
                "key points",
                "related to",
                "infers",
            ):
                assert phrase.lower() not in content.lower()

    def test_no_index_when_disabled(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        config = VaultAdapterConfig(generate_index=False)
        plan = build_vault_plan(wiki_dir, vault_dir, config=config)
        assert not plan.index_notes

        result = apply_vault_plan(plan)
        assert result.index_notes_written == 0
        assert not (vault_dir / INDEX_SUBDIR).exists()


# ---------------------------------------------------------------------------
# 10. Manifest generation deterministic
# ---------------------------------------------------------------------------

class TestManifestGeneration:
    def test_manifest_written(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.manifest_written is True
        manifest = vault_dir / MANIFEST_FILENAME
        assert manifest.exists()

    def test_manifest_valid_json(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.manifest_written is True
        manifest_data = json.loads(
            (vault_dir / MANIFEST_FILENAME).read_text(encoding="utf-8")
        )
        assert "version" in manifest_data
        assert "notes" in manifest_data
        assert manifest_data["total_notes"] == 1

    def test_manifest_contains_note_identity(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, note_id="note_x")

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.manifest_written is True
        manifest_data = json.loads(
            (vault_dir / MANIFEST_FILENAME).read_text(encoding="utf-8")
        )
        assert manifest_data["notes"][0]["note_id"] == "note_x"

    def test_manifest_deterministic(self, tmp_path: Path):
        note_plans = [
            VaultNotePlan(
                source_path="/wiki/a.md",
                relative_source="a.md",
                destination_path="/vault/TraceVault/Notes/a.md",
                relative_destination="TraceVault/Notes/a.md",
                original_filename="a.md",
                note_id="note_a",
            ),
        ]
        m1 = build_vault_manifest("/wiki", "/vault", note_plans)
        m2 = build_vault_manifest("/wiki", "/vault", note_plans)
        # Exclude generated_at (timestamp) for determinism check
        del m1["generated_at"]
        del m2["generated_at"]
        assert m1 == m2


# ---------------------------------------------------------------------------
# 11. No .obsidian directory created
# ---------------------------------------------------------------------------

class TestNoObsidianDir:
    def test_no_obsidian_directory_created(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert not (vault_dir / ".obsidian").exists()

    def test_no_obsidian_config_files(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert not (vault_dir / ".obsidian").exists()
        # Walk vault to ensure no .obsidian anywhere
        all_entries = list(vault_dir.rglob("*"))
        obsidian_entries = [e for e in all_entries if ".obsidian" in str(e)]
        assert not obsidian_entries


# ---------------------------------------------------------------------------
# 12. No LLM/model/external dependency paths
# ---------------------------------------------------------------------------

class TestNoExternalDependencies:
    def test_no_ollama_import(self):
        """Vault adapter must not import ollama."""
        import tracevault.wiki.vault.adapter as mod
        source = Path(mod.__file__).read_text()
        assert "ollama" not in source.lower()

    def test_no_llm_api_import(self):
        """Vault adapter must not import LLM APIs."""
        import tracevault.wiki.vault.adapter as mod
        source = Path(mod.__file__).read_text()
        for forbidden in ("openai", "anthropic", "litellm", "transformers"):
            assert forbidden not in source.lower()

    def test_no_http_request(self):
        """Vault adapter must not make HTTP requests."""
        import tracevault.wiki.vault.adapter as mod
        source = Path(mod.__file__).read_text()
        for forbidden in ("requests.", "httpx.", "urllib", "aiohttp"):
            assert forbidden not in source


# ---------------------------------------------------------------------------
# 13. Adaptation result model
# ---------------------------------------------------------------------------

class TestAdaptationResult:
    def test_success_property(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.success is True
        assert result.notes_copied == 1

    def test_to_dict(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        d = result.to_dict()
        assert "notes_copied" in d
        assert "success" in d
        assert d["notes_copied"] == 1


# ---------------------------------------------------------------------------
# 14. Multiple notes batch
# ---------------------------------------------------------------------------

class TestBatchAdaptation:
    def test_multiple_notes_copied(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir, title="A", note_id="n_a")
        _write_validated_note_to_wiki(wiki_dir, title="B", note_id="n_b")
        _write_validated_note_to_wiki(wiki_dir, title="C", note_id="n_c")

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)
        assert result.notes_copied == 3
        notes_dir = vault_dir / NOTES_SUBDIR
        assert len(list(notes_dir.glob("*.md"))) == 3

    def test_plan_to_dict(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note_to_wiki(wiki_dir)

        plan = build_vault_plan(wiki_dir, vault_dir)
        d = plan.to_dict()
        assert d["total_notes"] == 1
        assert d["accepted"] == 1
        assert d["rejected"] == 0
        assert "notes" in d
        assert "index_notes" in d


# ---------------------------------------------------------------------------
# 15. Health preflight fail-open guardrails
# ---------------------------------------------------------------------------

class TestHealthPreflightGuardrails:
    def test_adapt_writes_nothing_when_health_fails(self, tmp_path: Path):
        """adapt_to_obsidian_vault must not write any files when health fails."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        # Write two notes without frontmatter — health errors
        (wiki_dir / "bad1.md").write_text("# No Frontmatter\n")
        (wiki_dir / "bad2.md").write_text("# Also Bad\n")

        result = adapt_to_obsidian_vault(wiki_dir, vault_dir)

        assert vault_dir.exists() is False
        assert result.notes_copied == 0
        assert result.manifest_written is False
        assert result.errors

    def test_apply_rejects_plan_with_health_passed_false(self, tmp_path: Path):
        """apply_vault_plan must refuse a plan where health_passed is False."""
        plan = VaultAdaptationPlan(
            wiki_dir="/fake/wiki",
            vault_dir=str(tmp_path / "vault"),
            health_passed=False,
            health_errors=3,
            notes=[],
        )
        result = apply_vault_plan(plan)
        vault_dir = tmp_path / "vault"

        assert vault_dir.exists() is False
        assert result.notes_copied == 0
        assert result.manifest_written is False
        assert result.errors
        assert "Health preflight failed" in result.errors[0]

    def test_apply_rejects_plan_with_rejected_notes(self, tmp_path: Path):
        """apply_vault_plan must refuse a plan that contains rejected notes."""
        vault_dir = tmp_path / "vault"
        plan = VaultAdaptationPlan(
            wiki_dir="/fake/wiki",
            vault_dir=str(vault_dir),
            health_passed=True,
            notes=[
                VaultNotePlan(
                    source_path="/fake/note.md",
                    relative_source="note.md",
                    destination_path=str(vault_dir / "note.md"),
                    relative_destination="note.md",
                    original_filename="note.md",
                    rejected=True,
                    rejection_reason="some reason",
                ),
            ],
        )

        result = apply_vault_plan(plan)

        assert vault_dir.exists() is False
        assert result.notes_copied == 0
        assert result.errors


# ---------------------------------------------------------------------------
# 16. Intra-plan destination collision detection
# ---------------------------------------------------------------------------

class TestIntraPlanCollision:
    def test_build_plan_detects_same_basename_different_subdirs(
        self, tmp_path: Path
    ):
        """Two notes in different subdirs with same basename → collision."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        _write_synthetic_note(
            wiki_dir / "sub_a",
            "same.md",
            "---\nnote_id: a\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# A\n",
        )
        _write_synthetic_note(
            wiki_dir / "sub_b",
            "same.md",
            "---\nnote_id: b\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# B\n",
        )

        config = VaultAdapterConfig(allow_unhealthy=True)
        plan = build_vault_plan(wiki_dir, vault_dir, config=config)

        assert len(plan.notes) == 2
        accepted = [n for n in plan.notes if not n.rejected]
        rejected = plan.rejected_notes
        assert len(accepted) == 1
        assert len(rejected) == 1
        assert rejected[0].collision is True
        assert "Duplicate destination" in rejected[0].rejection_reason

    def test_apply_defensively_rejects_duplicate_destination(
        self, tmp_path: Path
    ):
        """Even a hand-crafted plan with duplicate destinations is refused."""
        vault_dir = tmp_path / "vault"
        plan = VaultAdaptationPlan(
            wiki_dir="/fake/wiki",
            vault_dir=str(vault_dir),
            health_passed=True,
            notes=[
                VaultNotePlan(
                    source_path="/fake/a.md",
                    relative_source="a.md",
                    destination_path=str(vault_dir / "x.md"),
                    relative_destination="x.md",
                    original_filename="x.md",
                ),
                VaultNotePlan(
                    source_path="/fake/b.md",
                    relative_source="b.md",
                    destination_path=str(vault_dir / "x.md"),
                    relative_destination="x.md",
                    original_filename="x.md",
                ),
            ],
        )

        result = apply_vault_plan(plan)

        assert vault_dir.exists() is False
        assert result.notes_copied == 0
        assert result.errors
        assert "Duplicate destination" in result.errors[0]


# ---------------------------------------------------------------------------
# 17. Byte-preserving copy (CRLF, BOM)
# ---------------------------------------------------------------------------

class TestBytePreservingCopy:
    def test_crlf_line_endings_preserved(self, tmp_path: Path):
        """Copied Markdown bytes must be exactly preserved, including CRLF."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()

        content = "---\nnote_id: x\nnote_type: t\nstatus: published\nevidence_count: 0\n---\r\n# Title\r\n\r\nBody\r\n"
        (wiki_dir / "note.md").write_bytes(content.encode("utf-8"))

        config = VaultAdapterConfig(allow_unhealthy=True)
        result = adapt_to_obsidian_vault(wiki_dir, vault_dir, config=config)

        assert result.notes_copied == 1
        copied = (vault_dir / "TraceVault" / "Notes" / "note.md")
        assert copied.read_bytes() == content.encode("utf-8")

    def test_bom_preserved(self, tmp_path: Path):
        """Copied Markdown with UTF-8 BOM must preserve BOM bytes."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()

        content = "﻿---\nnote_id: x\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# Title\n"
        (wiki_dir / "note.md").write_bytes(content.encode("utf-8"))

        config = VaultAdapterConfig(allow_unhealthy=True)
        result = adapt_to_obsidian_vault(wiki_dir, vault_dir, config=config)

        assert result.notes_copied == 1
        copied = (vault_dir / "TraceVault" / "Notes" / "note.md")
        assert copied.read_bytes() == content.encode("utf-8")


# ---------------------------------------------------------------------------
# 18. Lazy export regression
# ---------------------------------------------------------------------------

class TestWikiLazyExport:
    def test_build_vault_plan_via_wiki_module(self):
        """tracevault.wiki.build_vault_plan must be accessible via lazy import."""
        from tracevault import wiki
        assert hasattr(wiki, "build_vault_plan")
        assert callable(wiki.build_vault_plan)

    def test_apply_vault_plan_via_wiki_module(self):
        """tracevault.wiki.apply_vault_plan must be accessible via lazy import."""
        from tracevault import wiki
        assert hasattr(wiki, "apply_vault_plan")
        assert callable(wiki.apply_vault_plan)

    def test_adapt_to_obsidian_vault_via_wiki_module(self):
        """tracevault.wiki.adapt_to_obsidian_vault must be accessible via lazy import."""
        from tracevault import wiki
        assert hasattr(wiki, "adapt_to_obsidian_vault")
        assert callable(wiki.adapt_to_obsidian_vault)

    def test_vault_models_via_wiki_module(self):
        """Phase 6C model classes must be accessible via lazy import."""
        from tracevault import wiki
        assert hasattr(wiki, "VaultAdaptationPlan")
        assert hasattr(wiki, "VaultAdaptationResult")
        assert hasattr(wiki, "VaultAdapterConfig")
        assert hasattr(wiki, "VaultNotePlan")
        assert hasattr(wiki, "VaultIndexPlan")

    def test_lazy_import_caching(self):
        """First access caches the symbol; second access returns same object."""
        from tracevault import wiki
        first = wiki.build_vault_plan
        second = wiki.build_vault_plan
        assert first is second

    def test_unknown_attribute_raises_attribute_error(self):
        """Unknown attributes must raise AttributeError, not KeyError."""
        from tracevault import wiki
        with pytest.raises(AttributeError, match="not_a_real_phase_6c_symbol"):
            _ = wiki.not_a_real_phase_6c_symbol


# ---------------------------------------------------------------------------
# 19. .gitignore runtime output protection
# ---------------------------------------------------------------------------

class TestGitignoreRuntimeProtection:
    def test_gitignore_contains_recursive_tracevault_vault_output(self):
        """.gitignore must use recursive patterns to protect nested generated output."""
        gitignore = Path(__file__).resolve().parent.parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")

        assert "**/TraceVault/" in content
        assert "**/tracevault-vault-manifest.json" in content

    def test_gitignore_does_not_hide_source(self):
        """.gitignore must not accidentally hide source package folders."""
        gitignore = Path(__file__).resolve().parent.parent.parent / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines()

        # Source module should not be ignored
        # Check each non-comment, non-empty line for bare tracevault/ pattern
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # No line should match /tracevault/ (source root) or bare tracevault/
            if stripped in ("/tracevault/", "tracevault/"):
                raise AssertionError(f"gitignore line '{stripped}' would hide source")

    def test_gitignore_ignores_nested_tracevault_dir(self):
        """Nested TraceVault/ directories must be ignored at any depth."""
        import subprocess

        root = Path(__file__).resolve().parent.parent.parent
        # These paths don't need to exist — git check-ignore works on paths
        for path in (
            "local-vault/TraceVault/test.md",
            "vault/TraceVault/Notes/x.md",
            "tmp/some-vault/TraceVault/a.md",
        ):
            result = subprocess.run(
                ["git", "check-ignore", "-q", path],
                cwd=str(root),
                capture_output=True,
            )
            assert result.returncode == 0, (
                f"Path '{path}' was not ignored by .gitignore"
            )

    def test_gitignore_ignores_nested_manifest(self):
        """Nested tracevault-vault-manifest.json must be ignored at any depth."""
        import subprocess

        root = Path(__file__).resolve().parent.parent.parent
        for path in (
            "local-vault/tracevault-vault-manifest.json",
            "tmp/some-vault/tracevault-vault-manifest.json",
        ):
            result = subprocess.run(
                ["git", "check-ignore", "-q", path],
                cwd=str(root),
                capture_output=True,
            )
            assert result.returncode == 0, (
                f"Path '{path}' was not ignored by .gitignore"
            )

    def test_gitignore_does_not_ignore_source_vault_module(self):
        """src/tracevault/wiki/vault/ must NOT be ignored by gitignore."""
        import subprocess

        root = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            ["git", "check-ignore", "-q", "src/tracevault/wiki/vault/adapter.py"],
            cwd=str(root),
            capture_output=True,
        )
        assert result.returncode != 0, (
            "src/tracevault/wiki/vault/adapter.py should NOT be ignored"
        )
