"""Tests for wiki export data models."""

from tracevault.wiki.models import (
    WikiClaim,
    WikiEvidenceReference,
    WikiExportMetadata,
    WikiExportResult,
    WikiNote,
    WikiSourceChunk,
    WikiSourceDocument,
)


class TestWikiEvidenceReference:
    def test_minimal_construction(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        assert ref.label == "E1"
        assert ref.document_id == "doc_001"
        assert ref.chunk_id == "chunk_001"
        assert ref.source_path == ""
        assert ref.source_raw_hash == ""
        assert ref.raw_text_hash == ""
        assert ref.evidence_text_hash == ""
        assert ref.excerpt == ""

    def test_full_construction(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="srh123",
            raw_text_hash="abc123",
            evidence_text_hash="def456",
            excerpt="Source evidence text",
        )
        assert ref.source_path == "docs/test.md"
        assert ref.source_raw_hash == "srh123"
        assert ref.raw_text_hash == "abc123"
        assert ref.evidence_text_hash == "def456"
        assert ref.excerpt == "Source evidence text"

    def test_identity_key(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="srh",
            raw_text_hash="rth",
            evidence_text_hash="eth",
        )
        key = ref.identity_key()
        assert key == ("doc_001", "chunk_001", "srh", "rth", "eth", "E1")

    def test_identity_key_differs_for_different_chunk(self):
        ref1 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        ref2 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_002",
        )
        assert ref1.identity_key() != ref2.identity_key()

    def test_to_dict(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="srh",
            raw_text_hash="abc123",
            evidence_text_hash="def456",
            excerpt="Evidence text",
        )
        d = ref.to_dict()
        assert d["label"] == "E1"
        assert d["document_id"] == "doc_001"
        assert d["chunk_id"] == "chunk_001"
        assert d["source_path"] == "docs/test.md"
        assert d["source_raw_hash"] == "srh"
        assert d["raw_text_hash"] == "abc123"
        assert d["evidence_text_hash"] == "def456"
        assert d["excerpt"] == "Evidence text"


class TestWikiClaim:
    def test_claim_with_evidence(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="The system uses SHA-256", evidence_refs=[ref])
        assert claim.statement == "The system uses SHA-256"
        assert len(claim.evidence_refs) == 1
        assert claim.unsupported is False

    def test_claim_unsupported(self):
        claim = WikiClaim(statement="No evidence for this", unsupported=True)
        assert claim.unsupported is True
        assert len(claim.evidence_refs) == 0

    def test_has_evidence_true(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="A fact", evidence_refs=[ref])
        assert claim.has_evidence is True

    def test_has_evidence_false(self):
        claim = WikiClaim(statement="No proof")
        assert claim.has_evidence is False

    def test_is_supported_true(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="A fact", evidence_refs=[ref])
        assert claim.is_supported is True

    def test_is_supported_false_when_unsupported(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="No proof", unsupported=True, evidence_refs=[ref])
        assert claim.is_supported is False

    def test_is_supported_false_when_no_evidence(self):
        # supported=True but no evidence — the contract violation
        claim = WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])
        assert claim.is_supported is False

    def test_to_dict(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="A claim", evidence_refs=[ref])
        d = claim.to_dict()
        assert d["statement"] == "A claim"
        assert len(d["evidence_refs"]) == 1
        assert d["evidence_refs"][0]["label"] == "E1"
        assert d["unsupported"] is False


class TestWikiSourceDocument:
    def test_minimal(self):
        doc = WikiSourceDocument(document_id="doc_001")
        assert doc.source_path == ""
        assert doc.source_raw_hash == ""
        assert doc.content_hash == ""

    def test_full(self):
        doc = WikiSourceDocument(
            document_id="doc_001",
            source_path="docs/test.md",
            source_raw_hash="abc123",
            content_hash="def456",
        )
        assert doc.source_path == "docs/test.md"
        assert doc.source_raw_hash == "abc123"


class TestWikiSourceChunk:
    def test_minimal(self):
        chunk = WikiSourceChunk(document_id="doc_001", chunk_id="chunk_001")
        assert chunk.source_raw_hash == ""
        assert chunk.raw_text_hash == ""
        assert chunk.cleaned_text_hash == ""
        assert chunk.evidence_text_hash == ""

    def test_full(self):
        chunk = WikiSourceChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="srh",
            raw_text_hash="rth",
            cleaned_text_hash="cth",
            evidence_text_hash="eth",
        )
        assert chunk.source_raw_hash == "srh"
        assert chunk.raw_text_hash == "rth"
        assert chunk.cleaned_text_hash == "cth"
        assert chunk.evidence_text_hash == "eth"


class TestWikiExportMetadata:
    def test_defaults(self):
        meta = WikiExportMetadata(note_id="note_001", generated_at="2026-01-01T00:00:00+00:00")
        assert meta.note_type == "compiled_knowledge_wiki_note"
        assert meta.status == "proposal"
        assert meta.generated_by == "tracevault"
        assert meta.generator_version == "0.1.0"
        assert meta.schema_version == "wiki-export-v1"
        assert meta.source_policy == "raw_text_authoritative"
        assert meta.validation_status == "validation_required"
        assert meta.confidence == ""
        assert meta.evidence_count == 0
        assert meta.source_documents == []
        assert meta.source_chunks == []

    def test_generated_at_iso_with_string(self):
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_full(self):
        doc = WikiSourceDocument(document_id="doc_001", source_raw_hash="abc")
        chunk = WikiSourceChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc",
            evidence_text_hash="def",
        )
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
            evidence_count=2,
            source_documents=[doc],
            source_chunks=[chunk],
        )
        assert meta.validation_status == "validated"
        assert meta.evidence_count == 2
        assert len(meta.source_documents) == 1
        assert len(meta.source_chunks) == 1

    def test_to_dict(self):
        doc = WikiSourceDocument(document_id="doc_001", source_raw_hash="abc")
        chunk = WikiSourceChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc",
            evidence_text_hash="def",
        )
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
            evidence_count=1,
            source_documents=[doc],
            source_chunks=[chunk],
        )
        d = meta.to_dict()
        assert d["note_id"] == "note_001"
        assert d["note_type"] == "compiled_knowledge_wiki_note"
        assert d["status"] == "proposal"
        assert d["generated_at"] == "2026-01-01T00:00:00+00:00"
        assert d["generated_by"] == "tracevault"
        assert d["source_policy"] == "raw_text_authoritative"
        assert d["validation_status"] == "validated"
        assert d["evidence_count"] == 1
        assert d["schema_version"] == "wiki-export-v1"
        assert len(d["source_documents"]) == 1
        assert d["source_documents"][0]["document_id"] == "doc_001"
        assert d["source_documents"][0]["source_raw_hash"] == "abc"
        assert len(d["source_chunks"]) == 1
        assert d["source_chunks"][0]["chunk_id"] == "chunk_001"
        assert d["source_chunks"][0]["evidence_text_hash"] == "def"


class TestWikiNote:
    def test_minimal(self):
        note = WikiNote(note_id="note_001", title="Test Note")
        assert note.title == "Test Note"
        assert note.summary == ""
        assert note.claims == []
        assert note.source_evidence == []
        assert note.metadata is None

    def test_full(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="A fact", evidence_refs=[ref])
        doc = WikiSourceDocument(document_id="doc_001", source_raw_hash="abc")
        chunk = WikiSourceChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc",
            evidence_text_hash="def",
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
            title="Test Note",
            summary="A summary",
            claims=[claim],
            source_evidence=[ref],
            metadata=meta,
        )
        assert note.summary == "A summary"
        assert len(note.claims) == 1
        assert len(note.source_evidence) == 1
        assert note.metadata is not None

    def test_to_dict(self):
        note = WikiNote(note_id="note_001", title="Test Note")
        d = note.to_dict()
        assert d["note_id"] == "note_001"
        assert d["title"] == "Test Note"
        assert d["summary"] == ""
        assert d["claims"] == []
        assert d["metadata"] is None

    def test_unsupported_claims(self):
        note = WikiNote(
            note_id="note_001",
            title="T",
            claims=[
                WikiClaim(statement="Proven", evidence_refs=[
                    WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001"),
                ]),
                WikiClaim(statement="No proof", unsupported=True),
            ],
        )
        assert len(note.unsupported_claims()) == 1
        assert note.unsupported_claims()[0].statement == "No proof"

    def test_invalid_supported_claims(self):
        note = WikiNote(
            note_id="note_001",
            title="T",
            claims=[
                WikiClaim(statement="Proven", evidence_refs=[
                    WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001"),
                ]),
                WikiClaim(statement="No refs", unsupported=False, evidence_refs=[]),
            ],
        )
        assert len(note.invalid_supported_claims()) == 1
        assert note.invalid_supported_claims()[0].statement == "No refs"

    def test_validate_claim_coverage(self):
        note = WikiNote(
            note_id="note_001",
            title="T",
            claims=[
                WikiClaim(statement="Proven", evidence_refs=[
                    WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001"),
                ]),
                WikiClaim(statement="No refs", unsupported=False, evidence_refs=[]),
            ],
        )
        errors = note.validate_claim_coverage()
        assert len(errors) == 1
        assert "No refs" in errors[0]

    def test_validate_claim_coverage_clean(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        note = WikiNote(
            note_id="note_001",
            title="T",
            claims=[
                WikiClaim(statement="Proven", evidence_refs=[ref]),
                WikiClaim(statement="Unsupported ok", unsupported=True),
            ],
        )
        errors = note.validate_claim_coverage()
        assert errors == []


class TestWikiNoteValidate:
    """validate() method: identity consistency + claim coverage."""

    def test_validate_returns_error_for_mismatched_note_id(self):
        """note.note_id != metadata.note_id should produce an error."""
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_a",
            title="Mismatch",
            metadata=meta,
        )
        errors = note.validate()
        assert len(errors) == 1
        assert "note_id mismatch" in errors[0]
        assert "note_a" in errors[0]
        assert "note_b" in errors[0]

    def test_validate_passes_when_note_id_matches(self):
        """Matching note.note_id == metadata.note_id should not error."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Match",
            metadata=meta,
        )
        errors = note.validate()
        assert errors == []

    def test_validate_skips_identity_check_when_no_metadata(self):
        """No metadata means no identity mismatch check."""
        note = WikiNote(
            note_id="note_001",
            title="No metadata",
            metadata=None,
        )
        errors = note.validate()
        assert errors == []

    def test_validate_catches_both_identity_and_claim_errors(self):
        """validate() aggregates identity + claim coverage errors."""
        ref = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = WikiExportMetadata(
            note_id="wrong_id",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
        )
        note = WikiNote(
            note_id="note_001",
            title="Both Bad",
            claims=[
                WikiClaim(statement="Good claim", evidence_refs=[ref]),
                WikiClaim(statement="No refs", unsupported=False, evidence_refs=[]),
            ],
            metadata=meta,
        )
        errors = note.validate()
        assert len(errors) == 2
        assert "note_id mismatch" in errors[0]
        assert "no evidence refs" in errors[1]

    def test_validate_does_not_auto_correct(self):
        """validate() must not mutate note_id or metadata.note_id."""
        meta = WikiExportMetadata(
            note_id="note_b",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        note = WikiNote(
            note_id="note_a",
            title="Immutable",
            metadata=meta,
        )
        note.validate()
        assert note.note_id == "note_a"
        assert note.metadata.note_id == "note_b"


class TestWikiExportResult:
    def test_written(self):
        result = WikiExportResult(
            note_id="note_001",
            file_path="output/test-note.md",
            markdown="# Test",
            written=True,
        )
        assert result.written is True
        assert result.skipped is False
        assert result.rejected is False

    def test_skipped(self):
        result = WikiExportResult(
            note_id="note_001",
            file_path="output/test-note.md",
            markdown="# Test",
            written=False,
            skipped=True,
            reason="File already exists",
        )
        assert result.written is False
        assert result.skipped is True
        assert result.rejected is False
        assert result.reason == "File already exists"

    def test_rejected(self):
        result = WikiExportResult(
            note_id="note_001",
            file_path="output/test-note.md",
            markdown="",
            written=False,
            skipped=False,
            rejected=True,
            reason="Note is not validated",
        )
        assert result.rejected is True
        assert result.skipped is False
        assert result.written is False
        assert result.markdown == ""
