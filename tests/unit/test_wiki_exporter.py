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
        assert (tmp_path / "test-note--id-6e6f74655f303031.md").exists()

    def test_skips_existing_file(self, tmp_path: Path):
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.written is False
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"
        assert existing.read_text() == "existing content"

    def test_overwrites_with_allow_overwrite(self, tmp_path: Path):
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
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
        assert (tmp_path / "deep" / "nested" / "test-note--id-6e6f74655f303031.md").exists()


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
        assert "metadata" in result.reason.lower()

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
        assert not (tmp_path / "bad-note--id-6e6f74655f303031.md").exists()


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
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
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
    def test_markdown_in_result_on_written(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert result.written is True
        assert "# Test Note" in result.markdown

    def test_markdown_empty_on_skipped(self, tmp_path: Path):
        """Skipped result has empty markdown (skip happens before render)."""
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.skipped is True
        assert result.markdown == ""

    def test_file_path_in_result(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert "test-note" in result.file_path
        assert "6e6f74655f303031" in result.file_path

    def test_file_content_matches_markdown(self, tmp_path: Path):
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        file_content = (tmp_path / "test-note--id-6e6f74655f303031.md").read_text(
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
        assert not (tmp_path / "mismatch--id-6e6f74655f61.md").exists()

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
        assert build_note_filename(note) == "ai-governance--id-6e6f74655f303031.md"

    def test_title_slug_only(self):
        """Special characters in title get normalized."""
        note = WikiNote(note_id="note_001", title="Hello! World?")
        assert build_note_filename(note) == "hello-world--id-6e6f74655f303031.md"

    def test_special_chars_in_note_id(self):
        """Special chars in note_id are hex-encoded."""
        note = WikiNote(note_id="note--001", title="Test")
        assert build_note_filename(note) == "test--id-6e6f74652d2d303031.md"

    def test_empty_title_uses_note_id(self):
        """Empty title slug falls back to note_id only."""
        note = WikiNote(note_id="note_001", title="")
        assert build_note_filename(note) == "id-6e6f74655f303031.md"

    def test_special_chars_only_title_includes_note_id(self):
        """Title that slugifies to fallback 'note' still includes note_id."""
        note = WikiNote(note_id="note_001", title="!!!")
        assert build_note_filename(note) == "note--id-6e6f74655f303031.md"

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
        assert (tmp_path / "ai-governance--id-6e6f74655f61.md").exists()
        assert (tmp_path / "ai-governance--id-6e6f74655f62.md").exists()

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
        assert "6e6f74655f303031" in result.file_path

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
        file_b = tmp_path / "ai-governance--id-6e6f74655f62.md"
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
        assert "6e6f74655f61" in result.file_path
        assert "6e6f74655f62" not in result.file_path


class TestEncodeNoteIdCaseInsensitiveFS:
    """Codex P2: case-insensitive filesystem safety for note_id encoding."""

    def test_case_only_note_id_difference_writes_both(self, tmp_path: Path):
        """'NoteA' and 'notea' with same title => two distinct files."""
        notes = [
            _make_validated_note(title="AI Governance", note_id="NoteA"),
            _make_validated_note(title="AI Governance", note_id="notea"),
        ]
        results = export_notes(notes, tmp_path)
        assert len(results) == 2
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path

    def test_case_only_note_id_paths_differ_on_case_insensitive_fs(
        self, tmp_path: Path
    ):
        """File paths differ even when compared case-insensitively."""
        notes = [
            _make_validated_note(title="AI Governance", note_id="NoteA"),
            _make_validated_note(title="AI Governance", note_id="notea"),
        ]
        results = export_notes(notes, tmp_path)
        path1 = Path(results[0].file_path)
        path2 = Path(results[1].file_path)
        # Lowercased filenames must differ — proves case-insensitive safety
        assert path1.name.lower() != path2.name.lower()

    def test_case_only_note_id_files_exist(self, tmp_path: Path):
        """Both case-variant files are written to disk."""
        notes = [
            _make_validated_note(title="AI Governance", note_id="NoteA"),
            _make_validated_note(title="AI Governance", note_id="notea"),
        ]
        export_notes(notes, tmp_path)
        assert (tmp_path / "ai-governance--id-4e6f746541.md").exists()
        assert (tmp_path / "ai-governance--id-6e6f746561.md").exists()


class TestEncodeNoteId:
    """Tests for encode_note_id_for_filename UTF-8 hex encoding."""

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

    def test_underscore_hex_encoded(self):
        """Underscore is hex-encoded to stay distinct from dash."""
        assert encode_note_id_for_filename("note_001") == "6e6f74655f303031"

    def test_dash_hex_encoded(self):
        """Dash is hex-encoded like any other character."""
        assert encode_note_id_for_filename("note-001") == "6e6f74652d303031"

    def test_dot_hex_encoded(self):
        """Dot is hex-encoded."""
        assert encode_note_id_for_filename("note.001") == "6e6f74652e303031"

    def test_slash_hex_encoded(self):
        """Slash is hex-encoded, not left as path separator."""
        assert encode_note_id_for_filename("note/001") == "6e6f74652f303031"

    def test_space_hex_encoded(self):
        """Space is hex-encoded."""
        assert encode_note_id_for_filename("note 001") == "6e6f746520303031"

    def test_non_ascii_hex_encoded(self):
        """Non-ASCII characters produce hex-encoded output."""
        encoded = encode_note_id_for_filename("โน้ต001")
        assert encoded != "โน้ต001"
        assert encoded != ""
        assert all(c in "0123456789abcdef" for c in encoded)

    def test_alphanumeric_hex_encoded(self):
        """Even alphanumeric characters are hex-encoded."""
        assert encode_note_id_for_filename("abc123") == "616263313233"

    def test_deterministic(self):
        """Same input produces same output every time."""
        val = encode_note_id_for_filename("note_001")
        assert val == encode_note_id_for_filename("note_001")

    def test_case_only_difference_distinct(self):
        """'NoteA' and 'notea' produce distinct hex encodings."""
        assert encode_note_id_for_filename("NoteA") != encode_note_id_for_filename("notea")
        assert encode_note_id_for_filename("NoteA") == "4e6f746541"
        assert encode_note_id_for_filename("notea") == "6e6f746561"

    def test_returns_lowercase_hex_only(self):
        """Encoded output contains only lowercase hex characters 0-9a-f."""
        for note_id in ("note_001", "NoteA", "notea", "โน้ต001", "note/001"):
            encoded = encode_note_id_for_filename(note_id)
            assert all(c in "0123456789abcdef" for c in encoded)

    def test_empty_after_strip_raises(self):
        """note_id that is empty or whitespace-only raises ValueError."""
        with pytest.raises(ValueError, match="note_id"):
            encode_note_id_for_filename("")
        with pytest.raises(ValueError, match="note_id"):
            encode_note_id_for_filename("   ")

    def test_preserves_leading_trailing_space_bytes(self):
        """A: 'note_001' and ' note_001 ' produce distinct encodings (no strip)."""
        assert (
            encode_note_id_for_filename("note_001")
            != encode_note_id_for_filename(" note_001 ")
        )

    def test_leading_trailing_space_hex_exact(self):
        """Exact hex of ' note_001 ' includes space bytes 20 at start and end."""
        assert encode_note_id_for_filename(" note_001 ") == "206e6f74655f30303120"

    def test_no_strip_normalization(self):
        """Note ID is encoded exactly, not stripped or normalized."""
        assert encode_note_id_for_filename("note_001") == "6e6f74655f303031"
        assert encode_note_id_for_filename(" note_001") == "206e6f74655f303031"
        assert encode_note_id_for_filename("note_001 ") == "6e6f74655f30303120"


class TestNoteIdLossySlugPrevention:
    """Codex P1: hex encoding must prevent lossy slug collisions."""

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
        assert (tmp_path / "same-title--id-6e6f74655f303031.md").exists()
        assert (tmp_path / "same-title--id-6e6f74652d303031.md").exists()

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
        assert (tmp_path / "test--id-6e6f74652f303031.md").exists()

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

    def test_export_note_rejects_whitespace_note_id(self, tmp_path: Path):
        """export_note returns rejected result for whitespace-only note_id."""
        note = WikiNote(note_id="   ", title="Test")
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "note_id" in result.reason.lower()


class TestMetadataMandatoryWithAllowUnvalidated:
    """Codex P2: allow_unvalidated should only relax validation_status,
    not allow metadata=None.  Structural proof-chain metadata must remain
    mandatory in strict export mode."""

    def test_strict_metadata_none_allow_unvalidated_true_rejected(
        self, tmp_path: Path
    ):
        """A: metadata=None + allow_unvalidated=True => rejected."""
        note = WikiNote(note_id="note_001", title="No Meta", metadata=None)
        result = export_note(note, tmp_path, allow_unvalidated=True)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "metadata" in result.reason.lower()

    def test_strict_metadata_none_allow_unvalidated_false_rejected(
        self, tmp_path: Path
    ):
        """B: metadata=None + allow_unvalidated=False => rejected."""
        note = WikiNote(note_id="note_001", title="No Meta", metadata=None)
        result = export_note(note, tmp_path, allow_unvalidated=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "metadata" in result.reason.lower()

    def test_strict_meta_present_unvalidated_with_allow_exports(
        self, tmp_path: Path
    ):
        """C: metadata present, validation_required + allow_unvalidated=True
        => exports successfully."""
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

    def test_strict_meta_present_unvalidated_without_allow_rejected(
        self, tmp_path: Path
    ):
        """D: metadata present, validation_required + allow_unvalidated=False
        => rejected."""
        note = WikiNote(
            note_id="note_001",
            title="Unvalidated",
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validation_required",
            ),
        )
        result = export_note(note, tmp_path, allow_unvalidated=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False

    def test_metadata_none_rejection_no_file_created(self, tmp_path: Path):
        """E: metadata=None rejection must not create any file."""
        note = WikiNote(note_id="note_001", title="No Meta", metadata=None)
        export_note(note, tmp_path, allow_unvalidated=True)
        assert list(tmp_path.iterdir()) == []


class TestNoteIdBytePreservingFilename:
    """Codex P2: note_id bytes preserved in filename encoding (no strip)."""

    def test_space_padded_note_id_exports_distinct_files(self, tmp_path: Path):
        """B: 'note_001' and ' note_001 ' with same title export to two files."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_002", chunk_id="chunk_002"
        )
        note1 = WikiNote(
            note_id="note_001",
            title="Same Title",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1])],
            source_evidence=[ref1],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
                evidence_count=1,
            ),
        )
        note2 = WikiNote(
            note_id=" note_001 ",
            title="Same Title",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref2])],
            source_evidence=[ref2],
            metadata=WikiExportMetadata(
                note_id=" note_001 ",
                generated_at=GENERATED_AT,
                validation_status="validated",
                evidence_count=1,
            ),
        )
        results = export_notes([note1, note2], tmp_path)
        assert results[0].written is True
        assert results[1].written is True
        assert results[0].file_path != results[1].file_path

    def test_space_padded_note_id_filenames_differ_case_insensitively(
        self, tmp_path: Path
    ):
        """C: path1.name.lower() != path2.name.lower() for 'note_001' vs ' note_001 '."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_002", chunk_id="chunk_002"
        )
        note1 = WikiNote(
            note_id="note_001",
            title="Same Title",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1])],
            source_evidence=[ref1],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
                evidence_count=1,
            ),
        )
        note2 = WikiNote(
            note_id=" note_001 ",
            title="Same Title",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref2])],
            source_evidence=[ref2],
            metadata=WikiExportMetadata(
                note_id=" note_001 ",
                generated_at=GENERATED_AT,
                validation_status="validated",
                evidence_count=1,
            ),
        )
        results = export_notes([note1, note2], tmp_path)
        path1 = Path(results[0].file_path)
        path2 = Path(results[1].file_path)
        assert path1.name.lower() != path2.name.lower()

    def test_filename_uses_note_note_id_bytes_not_stripped(self, tmp_path: Path):
        """G: filename hex suffix matches note.note_id bytes, not stripped."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        # " note_001 " encodes to 206e6f74655f30303120 (includes space bytes)
        note = WikiNote(
            note_id=" note_001 ",
            title="Test",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=WikiExportMetadata(
                note_id=" note_001 ",
                generated_at=GENERATED_AT,
                validation_status="validated",
                evidence_count=1,
            ),
        )
        result = export_note(note, tmp_path)
        assert result.written is True
        # Must contain the space-padded hex, not the stripped version
        assert "206e6f74655f30303120" in result.file_path
        assert "6e6f74655f303031" not in result.file_path.replace(
            "206e6f74655f30303120", ""
        )


class TestSkipBeforeRender:
    """Codex P2: export_note should check file existence before rendering
    to avoid wasted rendering work and prevent rendering errors on skipped
    notes."""

    def test_existing_file_skips_before_render(self, tmp_path: Path):
        """A: Existing file with allow_overwrite=False skips before render."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Test Note",
            metadata=meta,
        )
        existing = tmp_path / "test-note--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        result = export_note(note, tmp_path, strict=False)
        assert result.skipped is True
        assert result.written is False
        assert result.rejected is False
        assert result.reason == "File already exists"

    def test_skipped_result_does_not_raise_on_invalid_generated_at(
        self, tmp_path: Path
    ):
        """C: export_note returns skipped=True without raising."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Test Note",
            metadata=meta,
        )
        existing = tmp_path / "test-note--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        # Must not raise — file exists so render is skipped
        result = export_note(note, tmp_path, strict=False)
        assert result.skipped is True

    def test_skipped_result_has_empty_markdown(self, tmp_path: Path):
        """D: Skipped result markdown is empty (no render called)."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Test Note",
            metadata=meta,
        )
        existing = tmp_path / "test-note--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        result = export_note(note, tmp_path, strict=False)
        assert result.skipped is True
        assert result.markdown == ""

    def test_allow_overwrite_invalid_rendering_returns_rejected(
        self, tmp_path: Path
    ):
        """E: With allow_overwrite=True, invalid generated_at note with no
        existing file returns rejected=True (render failure)."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Test Note",
            metadata=meta,
        )
        result = export_note(note, tmp_path, allow_overwrite=True, strict=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "render" in result.reason.lower()
        assert result.markdown == ""

    def test_export_notes_continues_after_skip(self, tmp_path: Path):
        """F: export_notes() continues processing later notes when earlier
        note is skipped."""
        meta_bad = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        note1 = WikiNote(
            note_id="note_001",
            title="Test Note",
            metadata=meta_bad,
        )
        note2 = _make_validated_note(title="Good", note_id="note_002")

        # Pre-create note_001 file so it gets skipped (before render)
        existing = tmp_path / "test-note--id-6e6f74655f303031.md"
        existing.write_text("existing content")

        results = export_notes([note1, note2], tmp_path, strict=False)
        assert len(results) == 2
        assert results[0].skipped is True
        assert results[1].written is True

    def test_existing_non_destructive_skip_test_still_passes(
        self, tmp_path: Path
    ):
        """G: Existing skip test behavior preserved with new semantics."""
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
        existing.write_text("existing content")
        note = _make_validated_note(title="Existing")
        result = export_note(note, tmp_path, strict=False)
        assert result.written is False
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"
        assert existing.read_text() == "existing content"


class TestRenderFailureRejection:
    """Codex P1: Convert render failures into rejected export results.

    Render failures (e.g., invalid generated_at that raises during
    render) must produce rejected WikiExportResult objects instead of
    propagating exceptions, so export_notes() can continue the batch.
    """

    def _make_bad_generated_at_note(
        self, note_id="note_001", title="Test Note"
    ) -> WikiNote:
        """Create a note with invalid generated_at that fails during render."""
        meta = WikiExportMetadata(
            note_id=note_id,
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        return WikiNote(
            note_id=note_id,
            title=title,
            metadata=meta,
        )

    def test_render_failure_returns_rejected_not_exception(self, tmp_path: Path):
        """A: export_note() with invalid generated_at returns rejected=True,
        not exception."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False

    def test_rejected_render_has_empty_markdown(self, tmp_path: Path):
        """B: rejected render failure has written=False, skipped=False,
        markdown='.'."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert result.markdown == ""

    def test_rejected_reason_contains_render(self, tmp_path: Path):
        """C: reason contains 'render' or the underlying error message."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.rejected is True
        assert "render" in result.reason.lower()

    def test_no_file_written_on_render_failure(self, tmp_path: Path):
        """D: no file is written when render fails."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.rejected is True
        assert not (tmp_path / "test-note--id-6e6f74655f303031.md").exists()

    def test_export_notes_continues_after_render_failure(self, tmp_path: Path):
        """E: export_notes() continues after one render failure and
        writes later valid notes."""
        bad_note = self._make_bad_generated_at_note(note_id="note_bad")
        good_note = _make_validated_note(title="Good", note_id="note_good")

        results = export_notes([bad_note, good_note], tmp_path, strict=False)
        assert len(results) == 2
        assert results[0].rejected is True
        assert results[0].written is False
        assert results[1].written is True
        assert results[1].rejected is False

    def test_existing_file_skip_before_render_still_works(
        self, tmp_path: Path
    ):
        """F: existing file skip still happens before render even when
        note would fail rendering."""
        note = self._make_bad_generated_at_note()
        existing = tmp_path / "test-note--id-6e6f74655f303031.md"
        existing.write_text("existing content")

        result = export_note(note, tmp_path, strict=False)
        # Skip should happen before render, so we get skipped, not rejected
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"

    def test_allow_overwrite_render_failure_returns_rejected(
        self, tmp_path: Path
    ):
        """G: allow_overwrite=True with render failure returns rejected=True,
        not exception."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, allow_overwrite=True, strict=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert result.markdown == ""
        assert "render" in result.reason.lower()

    def test_rejected_result_file_path_computed(self, tmp_path: Path):
        """rejected result still has the computed target path."""
        note = self._make_bad_generated_at_note()
        result = export_note(note, tmp_path, strict=False)
        assert result.rejected is True
        assert "test-note" in result.file_path
        assert "6e6f74655f303031" in result.file_path


class TestFilesystemFailureRejection:
    """Codex P1: Catch filesystem write errors and return rejected result.

    If output_dir.mkdir or file_path.write_text fails (FileExistsError,
    PermissionError, OSError), export_note must return a rejected result
    instead of raising, so export_notes() can continue the batch.
    """

    def test_output_dir_is_existing_file_returns_rejected(self, tmp_path: Path):
        """A: output_dir path is an existing file => rejected, no exception."""
        not_a_dir = tmp_path / "not_a_dir"
        not_a_dir.write_text("this is a file, not a directory")
        note = _make_validated_note()
        result = export_note(note, not_a_dir, strict=False)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "filesystem" in result.reason.lower()

    def test_write_text_permission_error_returns_rejected(self, tmp_path: Path):
        """B: write_text raises PermissionError => rejected, no exception."""
        note = _make_validated_note()

        def patched_write_text(self_path, data, *args, **kwargs):
            raise PermissionError("denied")

        monkeypatch_ctx = pytest.MonkeyPatch()
        monkeypatch_ctx.setattr(Path, "write_text", patched_write_text)
        try:
            result = export_note(note, tmp_path, strict=False)
        finally:
            monkeypatch_ctx.undo()

        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert result.markdown == ""
        assert "PermissionError" in result.reason or "denied" in result.reason

    def test_export_notes_continues_after_filesystem_failure(self, tmp_path: Path):
        """C: export_notes() continues after one note fails due to
        filesystem error and writes later valid notes."""
        good_note = _make_validated_note(title="Good", note_id="note_good")

        # Make note_a target a path where write will fail
        note_bad_dir = _make_validated_note(title="Bad", note_id="note_a")

        # Create a file at the output_dir level so mkdir on subpath fails
        # Instead, monkeypatch write_text to fail only for the first call
        call_count = [0]

        def patched_write_text(self_path, data, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise PermissionError("denied")
            # Fall through to real impl for subsequent calls
            with self_path.open("w", encoding="utf-8") as f:
                f.write(data)

        monkeypatch_ctx = pytest.MonkeyPatch()
        monkeypatch_ctx.setattr(Path, "write_text", patched_write_text)
        try:
            # note_a exports first (fails write), note_good exports second (succeeds)
            results = export_notes([note_bad_dir, good_note], tmp_path, strict=False)
        finally:
            monkeypatch_ctx.undo()

        assert len(results) == 2
        assert results[0].rejected is True
        assert results[0].written is False
        assert results[1].written is True
        assert results[1].rejected is False

    def test_skip_before_render_wins_over_write(self, tmp_path: Path):
        """D: if target file exists and allow_overwrite=False, returns
        skipped=True and does not attempt write_text."""
        # Pre-create the target file
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
        existing.write_text("existing content")

        call_count = [0]

        def counting_write_text(self_path, data, *args, **kwargs):
            call_count[0] += 1

        monkeypatch_ctx = pytest.MonkeyPatch()
        monkeypatch_ctx.setattr(Path, "write_text", counting_write_text)
        try:
            note = _make_validated_note(title="Existing")
            result = export_note(note, tmp_path, strict=False)
        finally:
            monkeypatch_ctx.undo()

        assert result.skipped is True
        assert result.written is False
        assert result.rejected is False
        # write_text must not have been called since skip happens first
        assert call_count[0] == 0

    def test_allow_overwrite_with_write_failure_returns_rejected(
        self, tmp_path: Path
    ):
        """E: allow_overwrite=True + write failure => rejected, not exception."""
        existing = tmp_path / "existing--id-6e6f74655f303031.md"
        existing.write_text("old content")

        def patched_write_text(self_path, data, *args, **kwargs):
            raise PermissionError("denied")

        monkeypatch_ctx = pytest.MonkeyPatch()
        monkeypatch_ctx.setattr(Path, "write_text", patched_write_text)
        try:
            note = _make_validated_note(title="Existing")
            result = export_note(note, tmp_path, allow_overwrite=True, strict=False)
        finally:
            monkeypatch_ctx.undo()

        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "filesystem" in result.reason.lower()

    def test_filesystem_failure_markdown_empty(self, tmp_path: Path):
        """F: rejected due to filesystem failure has empty markdown."""
        not_a_dir = tmp_path / "not_a_dir"
        not_a_dir.write_text("this is a file, not a directory")
        note = _make_validated_note()
        result = export_note(note, not_a_dir, strict=False)
        assert result.rejected is True
        assert result.markdown == ""


class TestStrictExportRequiresEvidenceSourceIdentity:
    """Codex P1: Strict export rejects evidence refs missing document_id/chunk_id.

    A supported claim in strict mode must have evidence refs that each
    carry both document_id and chunk_id.  Missing means None, empty
    string, or whitespace-only.
    """

    def test_strict_rejects_missing_document_id(self, tmp_path: Path):
        """A: evidence_ref with document_id='' is rejected in strict mode."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="chunk_001")
        note = WikiNote(
            note_id="note_001",
            title="Missing Doc",
            claims=[WikiClaim(statement="No doc", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "document_id" in result.reason

    def test_strict_rejects_missing_chunk_id(self, tmp_path: Path):
        """B: evidence_ref with chunk_id='' is rejected in strict mode."""
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="Missing Chunk",
            claims=[WikiClaim(statement="No chunk", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        assert "chunk_id" in result.reason

    def test_strict_rejects_whitespace_document_id(self, tmp_path: Path):
        """C: evidence_ref with document_id='   ' is rejected."""
        ref = WikiEvidenceReference(label="E1", document_id="   ", chunk_id="chunk_001")
        note = WikiNote(
            note_id="note_001",
            title="Whitespace Doc",
            claims=[WikiClaim(statement="Whitespace doc", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert "document_id" in result.reason

    def test_strict_rejects_whitespace_chunk_id(self, tmp_path: Path):
        """D: evidence_ref with chunk_id='\t' is rejected."""
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="\t")
        note = WikiNote(
            note_id="note_001",
            title="Whitespace Chunk",
            claims=[WikiClaim(statement="Whitespace chunk", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert "chunk_id" in result.reason

    def test_strict_rejects_both_empty(self, tmp_path: Path):
        """E: both document_id and chunk_id empty."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="Both Empty",
            claims=[WikiClaim(statement="No identity", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.written is False
        assert result.skipped is False
        # Reason mentions at least one of the missing fields
        assert "document_id" in result.reason or "chunk_id" in result.reason

    def test_rejection_does_not_write_file(self, tmp_path: Path):
        """F: Rejection does not write any file."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="No Write",
            claims=[WikiClaim(statement="Blocked", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        export_note(note, tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_rejection_reason_mentions_field_names(self, tmp_path: Path):
        """G: Reason mentions document_id or chunk_id for debugging."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="Debug",
            claims=[WikiClaim(statement="X", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.reason  # non-empty
        assert "document_id" in result.reason or "chunk_id" in result.reason

    def test_valid_evidence_ref_exports_successfully(self, tmp_path: Path):
        """H: Valid evidence_ref with document_id+chunk_id exports."""
        note = _make_validated_note()
        result = export_note(note, tmp_path)
        assert result.written is True
        assert result.rejected is False

    def test_non_strict_allows_sparse_evidence_ref(self, tmp_path: Path):
        """I: Non-strict export still permits sparse evidence refs."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="Sparse",
            claims=[WikiClaim(statement="Sparse ref", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path, strict=False)
        assert result.written is True
        assert result.rejected is False

    def test_rejection_before_render(self, tmp_path: Path):
        """Rejection happens before render_note() — markdown is empty."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="")
        note = WikiNote(
            note_id="note_001",
            title="No Render",
            claims=[WikiClaim(statement="Blocked", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert result.markdown == ""

    def test_unsupported_claims_not_checked_for_source_identity(
        self, tmp_path: Path
    ):
        """Unsupported claims are skipped by the source identity check
        (they are caught by the separate unsupported-claim check)."""
        note = WikiNote(
            note_id="note_001",
            title="Unsupported",
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

    def test_export_notes_batch_continues_after_identity_rejection(
        self, tmp_path: Path
    ):
        """export_notes() continues after one identity-rejected note."""
        bad_ref = WikiEvidenceReference(
            label="E1", document_id="", chunk_id=""
        )
        bad_note = WikiNote(
            note_id="note_bad",
            title="Bad",
            claims=[WikiClaim(statement="Bad ref", evidence_refs=[bad_ref])],
            metadata=WikiExportMetadata(
                note_id="note_bad",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        good_note = _make_validated_note(title="Good", note_id="note_good")

        results = export_notes([bad_note, good_note], tmp_path)
        assert len(results) == 2
        assert results[0].rejected is True
        assert results[0].written is False
        assert results[1].written is True
        assert results[1].rejected is False

    def test_input_note_not_mutated_by_check(self, tmp_path: Path):
        """The source identity check must not mutate input evidence refs."""
        ref = WikiEvidenceReference(label="E1", document_id="", chunk_id="chunk_001")
        note = WikiNote(
            note_id="note_001",
            title="Immutable",
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        original = note.to_dict()
        export_note(note, tmp_path)
        assert note.to_dict() == original

    def test_mixed_refs_first_bad_ref_causes_rejection(self, tmp_path: Path):
        """When a claim has both good and bad refs, the first bad ref
        triggers rejection."""
        good_ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        bad_ref = WikiEvidenceReference(
            label="E2", document_id="", chunk_id=""
        )
        note = WikiNote(
            note_id="note_001",
            title="Mixed",
            claims=[WikiClaim(statement="Mixed refs", evidence_refs=[good_ref, bad_ref])],
            metadata=WikiExportMetadata(
                note_id="note_001",
                generated_at=GENERATED_AT,
                validation_status="validated",
            ),
        )
        result = export_note(note, tmp_path)
        assert result.rejected is True
        assert "E2" in result.reason

    def test_identity_key_fallback_not_removed(self):
        """identity_key still returns fallback for sparse refs."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id=""
        )
        # Fallback behavior preserved — has_required_source_identity
        # is a separate check, not a replacement for identity_key.
        assert ref.has_required_source_identity() is False
        assert ref.identity_key()[0] != "chunk"
