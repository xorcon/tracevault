"""Tests for wiki Markdown rendering."""

from datetime import datetime, timezone

from tracevault.wiki.markdown import render_note
from tracevault.wiki.models import (
    WikiClaim,
    WikiEvidenceReference,
    WikiExportMetadata,
    WikiNote,
    WikiSourceChunk,
    WikiSourceDocument,
)

GENERATED_AT = "2026-01-01T00:00:00+00:00"


def _make_validated_metadata(
    note_id="note_001",
    source_documents=None,
    source_chunks=None,
    evidence_count=0,
) -> WikiExportMetadata:
    return WikiExportMetadata(
        note_id=note_id,
        generated_at=GENERATED_AT,
        validation_status="validated",
        evidence_count=evidence_count,
        source_documents=source_documents or [],
        source_chunks=source_chunks or [],
    )


def _make_note(
    title="Test Note",
    summary="",
    claims=None,
    source_evidence=None,
    metadata=None,
    note_id="note_001",
) -> WikiNote:
    return WikiNote(
        note_id=note_id,
        title=title,
        summary=summary,
        claims=claims or [],
        source_evidence=source_evidence or [],
        metadata=metadata,
    )


class TestYamlFrontmatter:
    def test_frontmatter_present(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        lines = md.split("\n")
        assert lines[0] == "---"
        assert lines[1].startswith("note_id:")
        # Find closing frontmatter
        assert lines[2] == "note_type: compiled_knowledge_wiki_note"
        assert lines[3] == "status: proposal"

    def test_frontmatter_generated_at(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert f"generated_at: {GENERATED_AT}" in md

    def test_frontmatter_generated_by(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "generated_by: tracevault" in md

    def test_frontmatter_source_policy(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "source_policy: raw_text_authoritative" in md

    def test_frontmatter_validation_status(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "validation_status: validated" in md

    def test_frontmatter_schema_version(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "schema_version: wiki-export-v1" in md

    def test_frontmatter_generator_version(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "generator_version: 0.1.0" in md

    def test_frontmatter_evidence_count(self):
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(metadata=meta))
        assert "evidence_count: 3" in md

    def test_frontmatter_source_documents(self):
        doc = WikiSourceDocument(
            document_id="doc_001",
            source_path="docs/test.md",
            source_raw_hash="abc123",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert "source_documents:" in md
        assert "  - document_id: doc_001" in md
        assert "source_path: docs/test.md" in md
        assert "source_raw_hash: abc123" in md

    def test_frontmatter_source_chunks(self):
        chunk = WikiSourceChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc",
            evidence_text_hash="def",
        )
        meta = _make_validated_metadata(source_chunks=[chunk])
        md = render_note(_make_note(metadata=meta))
        assert "source_chunks:" in md
        assert "  - document_id: doc_001" in md
        assert "chunk_id: chunk_001" in md
        assert "source_raw_hash: abc" in md
        assert "evidence_text_hash: def" in md

    def test_no_metadata_omits_frontmatter_fields(self):
        md = render_note(_make_note())
        # Frontmatter delimiter present but no metadata fields
        lines = md.split("\n")
        assert lines[0] == "---"
        assert lines[1] == "---"


class TestRenderNoteDeterministic:
    def test_same_input_produces_same_output(self):
        note = _make_note(title="Deterministic", summary="Always the same")
        output1 = render_note(note)
        output2 = render_note(note)
        assert output1 == output2

    def test_different_title_produces_different_output(self):
        note1 = _make_note(title="Alpha")
        note2 = _make_note(title="Beta")
        assert render_note(note1) != render_note(note2)

    def test_datetime_generated_at_deterministic(self):
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=dt,
            validation_status="validated",
        )
        md = render_note(_make_note(metadata=meta))
        assert "generated_at: 2026-01-01T00:00:00+00:00" in md


class TestRenderNoteStructure:
    def test_title_rendered_as_h1(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(title="My Title", metadata=meta))
        assert "# My Title" in md

    def test_summary_rendered_when_present(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(title="T", summary="A summary paragraph", metadata=meta))
        assert "A summary paragraph" in md

    def test_claims_section_present(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(title="T", metadata=meta))
        assert "## Claims" in md

    def test_evidence_references_section_present(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(title="T", metadata=meta))
        assert "## Evidence References" in md

    def test_tracevault_metadata_section_present(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(title="T", metadata=meta))
        assert "## TraceVault Metadata" in md


class TestClaimToEvidenceMapping:
    def test_claim_with_single_evidence(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        claim = WikiClaim(statement="A fact", evidence_refs=[ref])
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(claims=[claim], source_evidence=[ref], metadata=meta))
        assert "[E1]" in md
        assert "A fact" in md

    def test_claim_with_multiple_evidence(self):
        ref1 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        ref2 = WikiEvidenceReference(label="E2", document_id="doc_002", chunk_id="chunk_002")
        claim = WikiClaim(statement="A complex fact", evidence_refs=[ref1, ref2])
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(claims=[claim], source_evidence=[ref1, ref2], metadata=meta))
        assert "[E1, E2]" in md

    def test_multiple_claims_with_different_refs(self):
        ref1 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        ref2 = WikiEvidenceReference(label="E2", document_id="doc_002", chunk_id="chunk_002")
        claims = [
            WikiClaim(statement="First", evidence_refs=[ref1]),
            WikiClaim(statement="Second", evidence_refs=[ref2]),
        ]
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(claims=claims, source_evidence=[ref1, ref2], metadata=meta))
        assert "First [E1]" in md
        assert "Second [E2]" in md

    def test_supported_claim_with_no_evidence_not_emit_empty_brackets(self):
        """A claim with unsupported=False and evidence_refs=[] must not
        render as 'claim []'.  It must be marked unsupported."""
        claim = WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])
        meta = _make_validated_metadata()
        md = render_note(_make_note(claims=[claim], metadata=meta))
        assert "No refs []" not in md
        assert "unsupported" in md


class TestUnsupportedClaimBehavior:
    def test_unsupported_claim_marked(self):
        meta = _make_validated_metadata()
        claim = WikiClaim(statement="No proof", unsupported=True)
        md = render_note(_make_note(claims=[claim], metadata=meta))
        assert "No proof" in md
        assert "unsupported" in md

    def test_unsupported_claim_format(self):
        meta = _make_validated_metadata()
        claim = WikiClaim(statement="Unproven statement", unsupported=True)
        md = render_note(_make_note(claims=[claim], metadata=meta))
        assert "*(unsupported — no evidence)*" in md


class TestEvidenceDeduplication:
    def test_same_label_different_chunk_renders_twice(self):
        """Two refs with same label but different chunk_id must both appear."""
        ref1 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        ref2 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_002")
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        # E1 should appear, and a disambiguated E1-2
        assert "E1" in md
        assert "E1-2" in md

    def test_disambiguated_labels_in_claim_mapping(self):
        """Claim-to-evidence mapping must point to disambiguated labels."""
        ref1 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        ref2 = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_002")
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        assert "[E1, E1-2]" in md

    def test_same_identity_deduped(self):
        """Two refs with identical identity should be deduplicated."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            raw_text_hash="abc",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        ))
        # Should appear once in evidence references section
        sections = md.split("## Evidence References")
        assert len(sections[1]) > 0  # section exists
        count = sections[1].count("### E1")
        assert count == 1


class TestEvidenceReferenceRendering:
    def test_evidence_ref_section_includes_document_and_chunk(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="srh123",
            raw_text_hash="abc123",
            evidence_text_hash="def456",
            excerpt="Evidence text here",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "### E1" in md
        assert "`doc_001`" in md
        assert "`chunk_001`" in md

    def test_evidence_ref_includes_source_raw_hash(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="srh123",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "`srh123`" in md

    def test_evidence_ref_includes_excerpt(self):
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="Important evidence text",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "> Important evidence text" in md


class TestMetadataRendering:
    def test_metadata_source_policy_rendered(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "source_policy: raw_text_authoritative" in md

    def test_metadata_validation_status_rendered(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert "validation_status: validated" in md

    def test_metadata_evidence_count_rendered(self):
        meta = _make_validated_metadata(evidence_count=5)
        md = render_note(_make_note(metadata=meta))
        assert "evidence_count: 5" in md

    def test_metadata_omits_optional_fields_when_none(self):
        md = render_note(_make_note(note_id="note_001", metadata=None))
        assert "generated_at:" not in md.split("## TraceVault Metadata")[1]


class TestSectionOrder:
    def test_sections_appear_in_correct_order(self):
        ref = WikiEvidenceReference(label="E1", document_id="doc_001", chunk_id="chunk_001")
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(
            _make_note(
                title="Ordered",
                summary="Summary text",
                claims=[WikiClaim(statement="Claim", evidence_refs=[ref])],
                source_evidence=[ref],
                metadata=meta,
            )
        )
        # Frontmatter first
        assert md.startswith("---")
        title_pos = md.index("# Ordered")
        summary_pos = md.index("Summary text")
        claims_pos = md.index("## Claims")
        evidence_pos = md.index("## Evidence References")
        metadata_pos = md.index("## TraceVault Metadata")
        assert title_pos < summary_pos < claims_pos < evidence_pos < metadata_pos
