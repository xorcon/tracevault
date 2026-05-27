"""Tests for Phase 6C — Obsidian Vault Adapter CLI commands.

Covers:
- wiki-vault-plan JSON output valid
- wiki-vault-adapt JSON output valid
- CLI non-zero on health failure
- Plan command writes nothing
- Adapt command non-destructive by default
"""

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    """Run the TraceVault CLI and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "tracevault"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _write_validated_note(wiki_dir: Path) -> None:
    """Write a minimal valid wiki note via the CLI test helper."""
    from tracevault.wiki.exporter import export_note
    from tracevault.wiki.models import (
        WikiClaim,
        WikiEvidenceReference,
        WikiExportMetadata,
        WikiNote,
        WikiSourceChunk,
        WikiSourceDocument,
    )

    ref = WikiEvidenceReference(label="E1", document_id="doc_1", chunk_id="c_1")
    doc = WikiSourceDocument(document_id="doc_1", source_raw_hash="abc")
    chunk = WikiSourceChunk(
        document_id="doc_1",
        chunk_id="c_1",
        source_raw_hash="abc",
    )
    meta = WikiExportMetadata(
        note_id="note_001",
        generated_at="2026-01-01T00:00:00+00:00",
        validation_status="validated",
        evidence_count=1,
        source_documents=[doc],
        source_chunks=[chunk],
    )
    note = WikiNote(
        note_id="note_001",
        title="CLI Test Note",
        claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
        source_evidence=[ref],
        metadata=meta,
    )
    export_note(note, wiki_dir, strict=False)


# ---------------------------------------------------------------------------
# wiki-vault-plan CLI tests
# ---------------------------------------------------------------------------

class TestWikiVaultPlanCLI:
    def test_plan_json_output_valid(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        result = _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
                "--json",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "total_notes" in output
        assert output["total_notes"] == 1
        assert output["health_passed"] is True

    def test_plan_writes_nothing(self, tmp_path: Path):
        """Plan command must not create any files."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        result = _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        # Vault dir should not exist — plan writes nothing
        assert not vault_dir.exists()

    def test_plan_non_zero_on_health_failure(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        # Write note without frontmatter
        (wiki_dir / "bad.md").write_text("# No Frontmatter\n")

        result = _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
                "--json",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["health_passed"] is False

    def test_plan_nonexistent_wiki_dir(self, tmp_path: Path):
        result = _run_cli(
            [
                "wiki-vault-plan",
                str(tmp_path / "nonexistent"),
                "--vault-dir", str(tmp_path / "vault"),
            ],
            cwd=str(tmp_path),
        )
        assert result.returncode != 0

    def test_plan_default_vault_dir(self, tmp_path: Path):
        """Default vault dir is <wiki_dir>/vault when --vault-dir omitted."""
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        result = _run_cli(
            ["wiki-vault-plan", str(wiki_dir), "--json"],
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["vault_dir"] == str(wiki_dir / "vault")


# ---------------------------------------------------------------------------
# wiki-vault-adapt CLI tests
# ---------------------------------------------------------------------------

class TestWikiVaultAdaptCLI:
    def test_adapt_json_output_valid(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        result = _run_cli(
            [
                "wiki-vault-adapt",
                str(wiki_dir),
                str(vault_dir),
                "--json",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["notes_copied"] == 1
        assert output["success"] is True

    def test_adapt_creates_vault_structure(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        result = _run_cli(
            ["wiki-vault-adapt", str(wiki_dir), str(vault_dir)],
            cwd=str(tmp_path),
        )

        assert result.returncode == 0
        assert (vault_dir / "TraceVault" / "Notes").exists()
        assert (vault_dir / "TraceVault" / "Index").exists()
        assert (vault_dir / "tracevault-vault-manifest.json").exists()

    def test_adapt_non_zero_on_health_failure(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "bad.md").write_text("# No Frontmatter\n")

        result = _run_cli(
            ["wiki-vault-adapt", str(wiki_dir), str(vault_dir)],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0

    def test_adapt_no_obsidian_dir(self, tmp_path: Path):
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        _write_validated_note(wiki_dir)

        _run_cli(
            ["wiki-vault-adapt", str(wiki_dir), str(vault_dir)],
            cwd=str(tmp_path),
        )

        assert not (vault_dir / ".obsidian").exists()

    def test_adapt_nonexistent_wiki_dir(self, tmp_path: Path):
        result = _run_cli(
            [
                "wiki-vault-adapt",
                str(tmp_path / "nonexistent"),
                str(tmp_path / "vault"),
            ],
            cwd=str(tmp_path),
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# CLI collision tests
# ---------------------------------------------------------------------------

class TestWikiVaultCollisionCLI:
    def test_plan_non_zero_on_duplicate_destination(self, tmp_path: Path):
        """CLI must exit non-zero when two notes map to the same destination."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        # Write two notes with same basename in different subdirectories
        for subdir in ("sub_a", "sub_b"):
            (wiki_dir / subdir / "same.md").write_text(
                "---\nnote_id: x\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# Note\n"
            )

        result = _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
                "--json",
                "--allow-unhealthy",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["rejected"] >= 1

    def test_adapt_non_zero_on_duplicate_destination(self, tmp_path: Path):
        """wiki-vault-adapt must exit non-zero with duplicate destinations."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        for subdir in ("sub_a", "sub_b"):
            (wiki_dir / subdir / "same.md").write_text(
                "---\nnote_id: x\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# Note\n"
            )

        result = _run_cli(
            [
                "wiki-vault-adapt",
                str(wiki_dir),
                str(vault_dir),
                "--json",
                "--allow-unhealthy",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0

    def test_plan_writes_nothing_on_collision(self, tmp_path: Path):
        """Plan command with collision must not create vault directory."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        for subdir in ("sub_a", "sub_b"):
            (wiki_dir / subdir / "same.md").write_text(
                "---\nnote_id: x\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# Note\n"
            )

        _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
                "--allow-unhealthy",
            ],
            cwd=str(tmp_path),
        )

        assert not vault_dir.exists()

    def test_plan_non_zero_on_case_only_collision(self, tmp_path: Path):
        """CLI must exit non-zero when A.md and a.md collide (case-insensitive)."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        # A.md in sub_a, a.md in sub_b — case-only collision
        (wiki_dir / "sub_a" / "A.md").write_text(
            "---\nnote_id: a\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# A\n"
        )
        (wiki_dir / "sub_b" / "a.md").write_text(
            "---\nnote_id: b\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# B\n"
        )

        result = _run_cli(
            [
                "wiki-vault-plan",
                str(wiki_dir),
                "--vault-dir", str(vault_dir),
                "--json",
                "--allow-unhealthy",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["rejected"] >= 1

    def test_adapt_non_zero_on_case_only_collision(self, tmp_path: Path):
        """wiki-vault-adapt must exit non-zero with case-only duplicate destinations."""
        wiki_dir = tmp_path / "wiki"
        vault_dir = tmp_path / "vault"
        wiki_dir.mkdir()
        (wiki_dir / "sub_a").mkdir()
        (wiki_dir / "sub_b").mkdir()

        (wiki_dir / "sub_a" / "A.md").write_text(
            "---\nnote_id: a\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# A\n"
        )
        (wiki_dir / "sub_b" / "a.md").write_text(
            "---\nnote_id: b\nnote_type: t\nstatus: published\nevidence_count: 0\n---\n# B\n"
        )

        result = _run_cli(
            [
                "wiki-vault-adapt",
                str(wiki_dir),
                str(vault_dir),
                "--json",
                "--allow-unhealthy",
            ],
            cwd=str(tmp_path),
        )

        assert result.returncode != 0
