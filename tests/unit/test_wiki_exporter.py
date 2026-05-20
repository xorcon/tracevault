"""Tests for wiki exporter non-destructive behavior and evidence contract."""

from pathlib import Path

from tracevault.wiki.exporter import export_note, export_notes
from tracevault.wiki.models import (
    WikiClaim,
    WikiEvidenceReference,
    WikiExportMetadata,
    WikiNote,
    WikiSourceChunk,
    WikiSourceDocument,
)

GENERATED_AT = "2026-01-01T00:00:00+00:00"


def _make_validated_note(
    title="Test Note",
    note_id="note_001",
    claims=None,
    source_evidence=None,
) -> WikiNote:
    ref = source_evidence or [
        WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
    ]
    if claims is None:
        claims = [WikiClaim(statement="A fact", evidence_refs=ref)]

    doc = WikiSourceDocument(document_id="doc_001", source_raw_hash="abc123")
    chunk = WikiSourceChunk(
        document_id="doc_001",
        chunk_id="chunk_001",
        source_raw_hash="abc123",
        evidence_text_hash="def456",
    )
    meta = WikiExportMetadata(
        note_id=note_id,
        generated_at=GENERATED_AT,
        validation_status="validated",
        evidence_count=len(ref) if isinstance(ref, list) else 1,
        source_documents=[doc],
        source_chunks=[chunk],
    )
    return WikiNote(
        note_id=note_id,
        title=title,
        claims=claims,
        source_evidence=ref if isinstance(ref, list) else [ref],
        metadata=meta,
    )


class TestExportNoteNonDestructive:
    def test_writes_new_file(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.written is True
        assert result.skipped is False
        assert result.rejected is False
        assert (tmp_path / "test-note.md").exists()

    def test_skips_existing_file(self, tmp_path: Path):
        existing = tmp_path / "existing.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.written is False
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"
        assert existing.read_text() == "existing content"

    def test_overwrites_with_allow_overwrite(self, tmp_path: Path):
        existing = tmp_path / "existing.md"
        existing.write_text("old content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, allow_overwrite=True)
        assert result.written is True
        assert result.skipped is False
        assert existing.read_text() != "old content"

    def test_creates_parent_directories(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path / "deep" / "nested", strict=False)
        assert result.written is True
        assert (tmp_path / "deep" / "nested" / "test-note.md").exists()


class TestExportNoteValidationGated:
    """Strict default export rejects unvalidated notes."""

    def test_rejects_unvalidated_note_by_default(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Unvalidated",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.skipped is False
        assert result.written is False
        assert "not validated" in result.reason.lower()

    def test_rejects_note_without_metadata(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="No Metadata",
            metadata=None,
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert "not validated" in result.reason.lower()

    def test_writes_validated_note(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert result.written is True
        assert result.rejected is False

    def test_allow_unvalidated_overrides(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Unvalidated",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path, allow_unvalidated=True)
        assert result.written is True
        assert result.rejected is False


class TestExportNoteStrictUnsupported:
    def test_rejects_unsupported_claim_by_default(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Bad Note",
            claims=[WikiClaim(statement="No proof", unsupported=True)],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.skipped is False
        assert "unsupported" in result.reason.lower()

    def test_allow_unsupported_overrides(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Bad Note",
            claims=[WikiClaim(statement="No proof", unsupported=True)],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path, allow_unsupported=True)
        assert result.written is True
        assert result.rejected is False

    def test_file_not_created_on_rejection(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Bad Note",
            claims=[WikiClaim(statement="No proof", unsupported=True)],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert not (tmp_path / "bad-note.md").exists()


class TestExportNoteClaimEvidenceContract:
    """Codex finding #1: supported claim with no evidence_refs is rejected."""

    def test_rejects_supported_claim_with_no_evidence(self, tmp_path: Path):
        """A claim with unsupported=False and evidence_refs=[] must be rejected."""
        note = WikiNote(
            note_id="note_001",
            title="Invalid",
            claims=[WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.skipped is False
        assert "no evidence refs" in result.reason.lower()

    def test_non_strict_allows_invalid_claim(self, tmp_path: Path):
        """Non-strict mode should render invalid claims without rejecting."""
        note = WikiNote(
            note_id="note_001",
            title="Invalid",
            claims=[WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path, strict=False)
        assert result.written is True
        assert result.rejected is False


class TestExportResultSemantics:
    """Codex finding #5: skipped vs rejected must be separated."""

    def test_skipped_not_rejected(self, tmp_path: Path):
        """Existing file without overwrite => skipped=True, rejected=False."""
        existing = tmp_path / "existing.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.skipped is True
        assert result.rejected is False
        assert result.written is False

    def test_rejected_not_skipped(self, tmp_path: Path):
        """Invalid note in strict mode => rejected=True, skipped=False."""
        note = WikiNote(
            note_id="note_001",
            title="Bad",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.skipped is False
        assert result.written is False

    def test_rejected_has_reason(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Bad",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.reason  # non-empty


class TestExportNoteOutput:
    def test_markdown_in_result(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert "# Test Note" in result.markdown

    def test_file_path_in_result(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert "test-note.md" in result.file_path

    def test_file_content_matches_markdown(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        file_content = (tmp_path / "test-note.md").read_text(encoding="utf-8")
        assert file_content == result.markdown

    def test_rejected_result_has_empty_markdown(self, tmp_path: Path):
        note = WikiNote(
            note_id="note_001",
            title="Bad",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.markdown == ""


class TestExportNoteNoMutation:
    def test_input_note_not_mutated(self, tmp_path: Path):
        note = _make_validated_note()
        original = note.to_dict()
        export_note(note, tmp_path)
        assert note.to_dict() == original


class TestExportNotes:
    def test_exports_multiple(self, tmp_path: Path):
        notes = [
            _make_validated_note(title="Alpha"),
            _make_validated_note(title="Beta", note_id="note_002"),
        ]
        results = export_notes(notes, tmp_path)
        assert len(results) == 2
        assert all(r.written for r in results)

    def test_strict_rejects_unsupported(self, tmp_path: Path):
        notes = [
            _make_validated_note(title="Good"),
            WikiNote(
                note_id="bad",
                title="Bad",
                claims=[WikiClaim(statement="No proof", unsupported=True)],
                metadata=WikiExportMetadata(
                    note_id="bad",
                    generated_at=GENERATED_AT,
                    validation_status="validated",
                ),
            ),
        ]
        results = export_notes(notes, tmp_path)
        assert len(results) == 2
        assert results[0].written is True
        assert results[1].rejected is True
        assert results[1].skipped is False

    def test_non_strict_allows_all(self, tmp_path: Path):
        notes = [
            _make_validated_note(title="Good"),
            WikiNote(
                note_id="bad",
                title="Bad",
                claims=[WikiClaim(statement="No proof", unsupported=True)],
                metadata=WikiExportMetadata(
                    note_id="bad",
                    generated_at=GENERATED_AT,
                    validation_status="validation_required",
                ),
            ),
        ]
        results = export_notes(notes, tmp_path, strict=False)
        assert len(results) == 2
        assert results[0].written is True
        assert results[1].written is True
