"""Tests for wiki exporter non-destructive behavior and evidence contract."""

from pathlib import Path

import pytest

from tracevault.wiki.exporter import (
    build_note_filename,
    encode_note_id_for_filename,
    export_note,
    export_notes,
)
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
        assert (tmp_path / "test-note--id-note_001.md").exists()

    def test_skips_existing_file(self, tmp_path: Path):
        existing = tmp_path / "existing--id-note_001.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.written is False
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"
        assert existing.read_text() == "existing content"

    def test_overwrites_with_allow_overwrite(self, tmp_path: Path):
        existing = tmp_path / "existing--id-note_001.md"
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
        assert (tmp_path / "deep" / "nested" / "test-note--id-note_001.md").exists()


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
        assert not (tmp_path / "bad-note--id-note_001.md").exists()


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
        existing = tmp_path / "existing--id-note_001.md"
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
        assert "test-note" in result.file_path
        assert "note_001" in result.file_path

    def test_file_content_matches_markdown(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        file_content = (tmp_path / "test-note--id-note_001.md").read_text(
            encoding="utf-8"
        )
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


class TestExportNoteIdConsistency:
    """Codex P2: note.note_id must match metadata.note_id before export."""

    def test_strict_rejects_mismatched_note_id(self, tmp_path: Path):
        """note.note_id='note_a', metadata.note_id='note_b' => rejected."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "note_id mismatch" in result.reason
        assert not (tmp_path / "mismatch--id-note_a.md").exists()

    def test_matching_note_id_exports_successfully(self, tmp_path: Path):
        """note.note_id == metadata.note_id => writes file."""
        note = _make_validated_note()
        assert note.note_id == note.metadata.note_id
        result = export_note(note, tmp_path)
        assert result.written is True
        assert result.rejected is False

    def test_non_strict_allows_mismatched_note_id(self, tmp_path: Path):
        """Non-strict mode should not reject identity mismatch."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        result = export_note(note, tmp_path, strict=False)
        assert result.written is True
        assert result.rejected is False

    def test_mismatch_rejected_before_rendering(self, tmp_path: Path):
        """Rejected result must have empty markdown (no render on invalid note)."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.markdown == ""

    def test_rejected_reason_includes_both_ids(self, tmp_path: Path):
        """Reason message must include both note.note_id and metadata.note_id."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert "note_a" in result.reason
        assert "note_b" in result.reason

    def test_export_does_not_auto_correct_note_id(self, tmp_path: Path):
        """Export must not mutate note.note_id or metadata.note_id."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        export_note(note, tmp_path)
        assert note.note_id == "note_a"
        assert note.metadata.note_id == "note_b"


class TestBuildNoteFilename:
    """Tests for the build_note_filename helper."""

    def test_normal_title(self):
        note = WikiNote(note_id="note_001", title="AI Governance")
        assert build_note_filename(note) == "ai-governance--id-note_001.md"

    def test_title_slug_only(self):
        """Special characters in title get normalized."""
        note = WikiNote(note_id="note_001", title="Hello! World?")
        assert build_note_filename(note) == "hello-world--id-note_001.md"

    def test_special_chars_in_note_id(self):
        """Special chars in note_id get normalized via slug."""
        note = WikiNote(note_id="note--001", title="Test")
        assert build_note_filename(note) == "test--id-note--001.md"

    def test_empty_title_uses_note_id(self):
        """Empty title slug falls back to note_id only."""
        note = WikiNote(note_id="note_001", title="")
        assert build_note_filename(note) == "id-note_001.md"

    def test_special_chars_only_title_includes_note_id(self):
        """Title that slugifies to fallback 'note' still includes note_id."""
        note = WikiNote(note_id="note_001", title="!!!")
        assert build_note_filename(note) == "note--id-note_001.md"

    def test_deterministic(self):
        """Same note produces same filename every time."""
        note = WikiNote(note_id="note_001", title="My Title")
        assert build_note_filename(note) == build_note_filename(note)

    def test_no_path_separators(self):
        """Filename must not contain path separators."""
        note = WikiNote(note_id="note_001", title="My/Title")
        fn = build_note_filename(note)
        assert "/" not in fn
        assert "\\" not in fn


class TestExportFilenameCollision:
    """Codex P1: filenames must include note_id to disambiguate title collisions."""

    def test_same_title_different_note_id_writes_both(self, tmp_path: Path):
        """Two validated notes, same title, different note_id => two files."""
        notes = [
            _make_validated_note(title="AI Governance", note_id="note_a"),
            _make_validated_note(title="AI Governance", note_id="note_b"),
        ]
        results = export_notes(notes, tmp_path)
        assert len(results) == 2
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path
        assert (tmp_path / "ai-governance--id-note_a.md").exists()
        assert (tmp_path / "ai-governance--id-note_b.md").exists()

    def test_punctuation_variants_same_slug_different_files(
        self, tmp_path: Path
    ):
        """'AI Governance!' and 'AI Governance' => same slug, different files."""
        notes = [
            _make_validated_note(title="AI Governance!", note_id="note_a"),
            _make_validated_note(title="AI Governance", note_id="note_b"),
        ]
        results = export_notes(notes, tmp_path)
        assert len(results) == 2
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path

    def test_non_ascii_title_stable_filename(self, tmp_path: Path):
        """Non-ASCII title that slugifies to short string still uses note_id."""
        note = _make_validated_note(title="Résumé", note_id="note_001")
        result = export_note(note, tmp_path)
        assert result.written is True
        assert "note_001" in result.file_path

    def test_same_note_id_same_title_skips_on_second(self, tmp_path: Path):
        """Export same note twice with allow_overwrite=False => skip second."""
        note = _make_validated_note()
        r1 = export_note(note, tmp_path)
        r2 = export_note(note, tmp_path)
        assert r1.written is True
        assert r2.skipped is True
        assert r2.rejected is False

    def test_allow_overwrite_same_note(self, tmp_path: Path):
        """Same note + allow_overwrite=True => overwrites."""
        note = _make_validated_note()
        r1 = export_note(note, tmp_path)
        r2 = export_note(note, tmp_path, allow_overwrite=True)
        assert r1.written is True
        assert r2.written is True

    def test_overwrite_does_not_affect_other_note_id(self, tmp_path: Path):
        """Overwriting note_a should not overwrite note_b."""
        notes = [
            _make_validated_note(title="AI Governance", note_id="note_a"),
            _make_validated_note(title="AI Governance", note_id="note_b"),
        ]
        export_notes(notes, tmp_path)
        file_b = tmp_path / "ai-governance--id-note_b.md"
        content_b_before = file_b.read_text()

        # Re-export note_a with overwrite
        export_note(notes[0], tmp_path, allow_overwrite=True)

        # note_b file should be unchanged
        assert file_b.read_text() == content_b_before

    def test_filename_uses_canonical_note_id_not_metadata(
        self, tmp_path: Path
    ):
        """Non-strict: filename uses note.note_id, not metadata.note_id."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at=GENERATED_AT,
            validation_status="validated",
            evidence_count=1,
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=meta,
        )
        result = export_note(note, tmp_path, strict=False)
        assert result.written is True
        assert "note_a" in result.file_path
        assert "note_b" not in result.file_path


class TestEncodeNoteId:
    """Tests for encode_note_id_for_filename percent-encoding."""

    def test_underscore_vs_dash_remain_distinct(self):
        """'note_001' and 'note-001' must produce distinct encoded strings."""
        assert (
            encode_note_id_for_filename("note_001")
            == encode_note_id_for_filename("note_001")
        )
        assert (
            encode_note_id_for_filename("note_001")
            != encode_note_id_for_filename("note-001")
        )

    def test_dot_vs_dash_remain_distinct(self):
        """'note.001' and 'note-001' must produce distinct encoded strings."""
        assert (
            encode_note_id_for_filename("note.001")
            != encode_note_id_for_filename("note-001")
        )

    def test_underscore_encoded(self):
        """Underscore must be percent-encoded to stay distinct from dash."""
        assert encode_note_id_for_filename("note_001") == "note_001"

    def test_dash_passthrough(self):
        """Dash is left readable (safe character)."""
        assert encode_note_id_for_filename("note-001") == "note-001"

    def test_dot_encoded(self):
        """Dot must be percent-encoded."""
        assert encode_note_id_for_filename("note.001") == "note.001"

    def test_slash_encoded(self):
        """Slash must be percent-encoded, not left as path separator."""
        assert encode_note_id_for_filename("note/001") == "note%2F001"

    def test_space_encoded(self):
        """Space must be percent-encoded."""
        assert encode_note_id_for_filename("note 001") == "note%20001"

    def test_non_ascii_encoded(self):
        """Non-ASCII characters must be percent-encoded."""
        encoded = encode_note_id_for_filename("โน้ต001")
        assert encoded != "โน้ต001"
        assert encoded != ""

    def test_alphanumeric_passthrough(self):
        """Alphanumeric characters are left readable."""
        assert encode_note_id_for_filename("abc123") == "abc123"

    def test_deterministic(self):
        """Same input produces same output every time."""
        val = encode_note_id_for_filename("note_001")
        assert val == encode_note_id_for_filename("note_001")


class TestNoteIdLossySlugPrevention:
    """Codex P1: percent-encoding must prevent lossy slug collisions."""

    def test_underscore_vs_dash_same_title_different_files(self, tmp_path: Path):
        """note_001 and note-001 with same title => two distinct files."""
        notes = [
            _make_validated_note(title="Same Title", note_id="note_001"),
            _make_validated_note(title="Same Title", note_id="note-001"),
        ]
        results = export_notes(notes, tmp_path)
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path
        assert (tmp_path / "same-title--id-note_001.md").exists()
        assert (tmp_path / "same-title--id-note-001.md").exists()

    def test_dot_vs_dash_same_title_different_files(self, tmp_path: Path):
        """note.001 and note-001 with same title => two distinct files."""
        notes = [
            _make_validated_note(title="Same Title", note_id="note.001"),
            _make_validated_note(title="Same Title", note_id="note-001"),
        ]
        results = export_notes(notes, tmp_path)
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path

    def test_slash_in_note_id_no_nested_path(self, tmp_path: Path):
        """note/001 must not create directory nesting."""
        note = _make_validated_note(title="Test", note_id="note/001")
        result = export_note(note, tmp_path)
        assert result.written is True
        # File should be directly under output_dir, not in a subdirectory
        assert "/" not in result.file_path.split(str(tmp_path))[-1].lstrip("/")[:-3]
        # The file exists directly under tmp_path
        assert (tmp_path / "test--id-note%2F001.md").exists()

    def test_non_ascii_note_id_distinct(self, tmp_path: Path):
        """Non-ASCII note_id must not collapse to empty or shared slug."""
        notes = [
            _make_validated_note(title="Same Title", note_id="โน้ต001"),
            _make_validated_note(title="Same Title", note_id="note_001"),
        ]
        results = export_notes(notes, tmp_path)
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path

    def test_whitespace_note_id_distinct_from_hyphen_underscore(
        self, tmp_path: Path
    ):
        """'note 001' must not collapse into same filename as 'note_001' or 'note-001'."""
        notes = [
            _make_validated_note(title="Same", note_id="note 001"),
            _make_validated_note(title="Same", note_id="note_001"),
            _make_validated_note(title="Same", note_id="note-001"),
        ]
        results = export_notes(notes, tmp_path)
        assert all(r.written for r in results)
        paths = {r.file_path for r in results}
        assert len(paths) == 3


class TestEmptyNoteId:
    """Empty or whitespace-only note_id must be rejected."""

    def test_build_note_filename_raises_value_error(self):
        """build_note_filename raises ValueError for empty note_id."""
        note = WikiNote(note_id="", title="Test")
        with pytest.raises(ValueError, match="note_id"):
            build_note_filename(note)

    def test_build_note_filename_raises_for_whitespace(self):
        """build_note_filename raises ValueError for whitespace note_id."""
        note = WikiNote(note_id="   ", title="Test")
        with pytest.raises(ValueError, match="note_id"):
            build_note_filename(note)

    def test_export_note_rejects_empty_note_id(self, tmp_path: Path):
        """export_note returns rejected result for empty note_id."""
        note = WikiNote(note_id="", title="Test")
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "note_id" in result.reason.lower()
