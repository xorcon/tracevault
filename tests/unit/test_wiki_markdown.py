"""Tests for wiki Markdown rendering."""

from datetime import datetime, timedelta, timezone

import pytest

from tracevault.wiki.markdown import _render_blockquote, render_note
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
        assert lines[2] == 'note_type: "compiled_knowledge_wiki_note"'
        assert lines[3] == 'status: "proposal"'

    def test_frontmatter_generated_at(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert f'generated_at: "{GENERATED_AT}"' in md

    def test_frontmatter_generated_by(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'generated_by: "tracevault"' in md

    def test_frontmatter_source_policy(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'source_policy: "raw_text_authoritative"' in md

    def test_frontmatter_validation_status(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'validation_status: "validated"' in md

    def test_frontmatter_schema_version(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'schema_version: "wiki-export-v1"' in md

    def test_frontmatter_generator_version(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'generator_version: "0.1.0"' in md

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
        assert '  - document_id: "doc_001"' in md
        assert 'source_path: "docs/test.md"' in md
        assert 'source_raw_hash: "abc123"' in md

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
        assert '  - document_id: "doc_001"' in md
        assert 'chunk_id: "chunk_001"' in md
        assert 'source_raw_hash: "abc"' in md
        assert 'evidence_text_hash: "def"' in md

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
        assert 'generated_at: "2026-01-01T00:00:00+00:00"' in md


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

    def test_invalid_supported_claim_has_balanced_italic_markers(self):
        """A claim with unsupported=False and no evidence refs must render
        with balanced *(...)* italic markers, not *(... without closing *."""
        claim = WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])
        meta = _make_validated_metadata()
        md = render_note(_make_note(claims=[claim], metadata=meta))
        assert "*(unsupported — no evidence refs)*" in md

    def test_invalid_supported_claim_does_not_have_malformed_marker(self):
        """The malformed open-only marker *(unsupported — no evidence refs)
        without closing * must not appear in rendered output."""
        claim = WikiClaim(statement="No refs", unsupported=False, evidence_refs=[])
        meta = _make_validated_metadata()
        md = render_note(_make_note(claims=[claim], metadata=meta))
        assert "*(unsupported — no evidence refs)" not in md.replace(
            "*(unsupported — no evidence refs)*", ""
        )


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
        assert 'source_policy: "raw_text_authoritative"' in md

    def test_metadata_validation_status_rendered(self):
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'validation_status: "validated"' in md

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


class TestYamlScalarQuoting:
    """Codex P2: YAML frontmatter string scalars must be safely quoted
    to prevent corruption from YAML-significant characters."""

    def test_frontmatter_quotes_normal_scalar_strings(self):
        """A: normal string values are double-quoted in frontmatter."""
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'note_id: "note_001"' in md
        assert 'note_type: "compiled_knowledge_wiki_note"' in md
        assert 'status: "proposal"' in md

    def test_source_path_with_hash_is_quoted(self):
        """B: source_path containing '#' is quoted, not raw plain scalar."""
        doc = WikiSourceDocument(
            document_id="doc_001",
            source_path="docs/notes#section-1.md",
            source_raw_hash="abc123",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert 'source_path: "docs/notes#section-1.md"' in md

    def test_source_path_with_colon_is_quoted(self):
        """C: source_path containing ':' is quoted."""
        doc = WikiSourceDocument(
            document_id="doc_001",
            source_path="C:\\Users\\docs\\test.md",
            source_raw_hash="abc123",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        # The colon in the path must be within quotes
        assert 'source_path: "' in md
        assert "C:" in md

    def test_yaml_boolean_like_document_id_remains_string(self):
        """D: document_id containing 'true', 'null', '123', or 'a: b'
        remains quoted as string, not interpreted as YAML bool/number/null."""
        doc = WikiSourceDocument(
            document_id="true",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert 'document_id: "true"' in md
        # Make sure it's not bare 'true' (YAML boolean)
        assert "document_id: true\n" not in md
        assert "document_id: true " not in md

    def test_null_like_document_id_remains_quoted(self):
        """D variant: 'null' document_id remains quoted."""
        doc = WikiSourceDocument(
            document_id="null",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert 'document_id: "null"' in md

    def test_numeric_like_document_id_remains_quoted(self):
        """D variant: '123' document_id remains quoted."""
        doc = WikiSourceDocument(
            document_id="123",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert 'document_id: "123"' in md

    def test_colon_space_in_value_remains_quoted(self):
        """D variant: value like 'a: b' remains quoted."""
        doc = WikiSourceDocument(
            document_id="a: b",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert 'document_id: "a: b"' in md

    def test_double_quote_in_value_is_escaped(self):
        """E: value containing double quote is escaped."""
        doc = WikiSourceDocument(
            document_id='doc "special"',
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert r'document_id: "doc \"special\""' in md

    def test_newline_in_value_is_escaped(self):
        """F: value containing newline is escaped as \\n."""
        doc = WikiSourceDocument(
            document_id="doc\nline2",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert r'document_id: "doc\nline2"' in md

    def test_evidence_count_remains_numeric(self):
        """G: evidence_count is emitted without quotes."""
        meta = _make_validated_metadata(evidence_count=42)
        md = render_note(_make_note(metadata=meta))
        assert "evidence_count: 42" in md
        # Must not be quoted
        assert '"42"' not in md

    def test_frontmatter_field_order_deterministic(self):
        """H: frontmatter fields appear in stable, deterministic order."""
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(metadata=meta))
        fm = md.split("---")[1]  # content between delimiters
        lines = fm.strip().split("\n")
        field_names = [line.split(":")[0].strip() for line in lines if ":" in line]
        # note_id should come before note_type, which comes before status
        assert field_names.index("note_id") < field_names.index("note_type")
        assert field_names.index("note_type") < field_names.index("status")
        assert field_names.index("status") < field_names.index("generated_at")
        assert field_names.index("generated_at") < field_names.index(
            "generated_by"
        )
        assert field_names.index("evidence_count") > field_names.index(
            "validation_status"
        )

    def test_optional_none_confidence_not_rendered(self):
        """I: confidence=None does not render in frontmatter."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence=None,  # explicitly None
        )
        md = render_note(_make_note(metadata=meta))
        # confidence=None should not render
        assert "confidence:" not in md


class TestConfidenceRendering:
    """Codex P2: zero confidence values must render in frontmatter."""

    def test_confidence_zero_int_renders(self):
        """A: confidence=0 renders in YAML frontmatter."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence=0,
        )
        md = render_note(_make_note(metadata=meta))
        assert "confidence: 0" in md

    def test_confidence_zero_float_renders(self):
        """B: confidence=0.0 renders in YAML frontmatter."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence=0.0,
        )
        md = render_note(_make_note(metadata=meta))
        assert "confidence: 0.0" in md

    def test_confidence_zero_string_renders_quoted(self):
        """C: confidence='0' renders as quoted string."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence="0",
        )
        md = render_note(_make_note(metadata=meta))
        assert 'confidence: "0"' in md

    def test_confidence_none_not_rendered(self):
        """D: confidence=None does not render."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence=None,
        )
        md = render_note(_make_note(metadata=meta))
        assert "confidence:" not in md

    def test_confidence_nonzero_renders(self):
        """E: existing nonzero string confidence still renders."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=GENERATED_AT,
            validation_status="validated",
            confidence="high",
        )
        md = render_note(_make_note(metadata=meta))
        assert 'confidence: "high"' in md


class TestGeneratedAtUtcNormalization:
    """Codex P2: generated_at_iso() normalizes to UTC."""

    def test_aware_non_utc_datetime_normalizes_to_utc(self):
        """A: +07:00 datetime converts to UTC."""
        dt = datetime(
            2026, 1, 1, 7, 0,
            tzinfo=timezone(timedelta(hours=7)),
        )
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=dt,
            validation_status="validated",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_naive_datetime_treated_as_utc(self):
        """B: naive datetime treated as UTC."""
        dt = datetime(2026, 1, 1, 0, 0)
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=dt,
            validation_status="validated",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_string_with_plus_offset_normalizes_to_utc(self):
        """C: string with +07:00 normalizes to +00:00."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T07:00:00+07:00",
            validation_status="validated",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_string_with_z_normalizes_to_utc(self):
        """D: string with Z normalizes to +00:00."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00Z",
            validation_status="validated",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_invalid_string_raises_value_error(self):
        """E: invalid string fails with ValueError (fail-closed)."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="not-a-datetime",
            validation_status="validated",
        )
        with pytest.raises(ValueError):
            meta.generated_at_iso()

    def test_frontmatter_uses_normalized_generated_at(self):
        """F: frontmatter rendered generated_at is UTC-normalized."""
        dt = datetime(
            2026, 1, 1, 7, 0,
            tzinfo=timezone(timedelta(hours=7)),
        )
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at=dt,
            validation_status="validated",
        )
        md = render_note(_make_note(metadata=meta))
        assert 'generated_at: "2026-01-01T00:00:00+00:00"' in md

    def test_existing_utc_string_stable(self):
        """G: existing UTC string timestamp remains unchanged."""
        meta = WikiExportMetadata(
            note_id="note_001",
            generated_at="2026-01-01T00:00:00+00:00",
            validation_status="validated",
        )
        assert meta.generated_at_iso() == "2026-01-01T00:00:00+00:00"

    def test_backslash_in_value_is_escaped(self):
        """Additional: backslash in value is escaped."""
        doc = WikiSourceDocument(
            document_id="doc\\path",
            source_raw_hash="abc",
        )
        meta = _make_validated_metadata(source_documents=[doc])
        md = render_note(_make_note(metadata=meta))
        assert r'document_id: "doc\\path"' in md

    def test_generated_at_with_colon_plus_quoted(self):
        """generated_at ISO timestamp with colons and + is quoted."""
        meta = _make_validated_metadata()
        md = render_note(_make_note(metadata=meta))
        assert 'generated_at: "2026-01-01T00:00:00+00:00"' in md


class TestMultiLineExcerptBlockquote:
    """Codex P3: every excerpt line must be quoted in evidence block."""

    def test_multiline_excerpt_every_line_quoted(self):
        """A: Multi-line excerpt renders every line with '> '."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="first line\nsecond line\nthird line",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "> first line" in md
        assert "> second line" in md
        assert "> third line" in md

    def test_blank_line_inside_excerpt_renders_as_quote(self):
        """B: Blank line inside excerpt renders as '>'."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="before\n\nafter",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        lines = md.split("\n")
        # Find the blank-line-within-quote region
        assert ">" in lines
        # The "before" and "after" lines should be quoted
        assert "> before" in md
        assert "> after" in md

    def test_single_line_excerpt_one_blockquote_line(self):
        """C: Single-line excerpt remains one blockquote line."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="single line only",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "> single line only" in md
        # Count how many lines in evidence section start with "> "
        evidence_section = md.split("## Evidence References")[1].split(
            "## TraceVault Metadata"
        )[0]
        blockquote_lines = [
            line for line in evidence_section.split("\n") if line.startswith("> ")
        ]
        assert len(blockquote_lines) == 1

    def test_excerpt_line_starting_with_gt_still_quoted(self):
        """D: Excerpt line that starts with '>' still receives quote prefix."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="normal line\n> already looks quoted",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        assert "> normal line" in md
        assert "> > already looks quoted" in md

    def test_no_excerpt_lines_appear_as_unquoted_body(self):
        """E: No excerpt lines appear as unquoted normal body text."""
        ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            excerpt="line one\nline two\nline three",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(source_evidence=[ref], metadata=meta))
        # Get the evidence section content
        evidence_section = md.split("## Evidence References")[1].split(
            "## TraceVault Metadata"
        )[0]
        lines = evidence_section.split("\n")
        for line in lines:
            # Each non-empty line in the evidence section should be
            # a metadata line or a blockquote line
            stripped = line.strip()
            if stripped and not stripped.startswith(">") and not stripped.startswith(
                "-"
            ) and not stripped.startswith("###") and stripped not in (
                "",
                "### E1",
                "- **Document**: `doc_001`",
            ):
                # If the line content is an excerpt line, it must be quoted
                if stripped in ("line one", "line two", "line three"):
                    raise AssertionError(f"Unquoted excerpt line found: {stripped}")

    def test_render_blockquote_helper_single_line(self):
        """_render_blockquote helper: single line."""
        result = _render_blockquote("hello")
        assert result == ["> hello"]

    def test_render_blockquote_helper_multiline(self):
        """_render_blockquote helper: multi-line with blank."""
        result = _render_blockquote("first\n\nsecond")
        assert result == ["> first", ">", "> second"]

    def test_render_blockquote_helper_trailing_newline(self):
        """_render_blockquote: trailing newline handled deterministically."""
        result = _render_blockquote("line one\nline two\n")
        # splitlines() drops the trailing empty element for a trailing \n
        assert result == ["> line one", "> line two"]


class TestEvidenceDedupByStableIdentity:
    """Codex P1: Deduplicate evidence by stable chunk identity.

    identity_key() is anchored on (document_id, chunk_id), not on
    optional hashes or label.  Sparse and full refs for the same
    chunk must render as one evidence entry with merged metadata.
    """

    def test_sparse_claim_ref_plus_full_source_evidence_one_entry(self):
        """A: Claim ref sparse + source_evidence full for same doc/chunk
        render as one evidence entry."""
        claim_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            # no hashes, no excerpt
        )
        source_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="abc123",
            raw_text_hash="def456",
            evidence_text_hash="ghi789",
            excerpt="Full evidence text here",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[claim_ref])],
            source_evidence=[source_ref],
            metadata=meta,
        ))
        # Only one E1 heading in evidence section
        evidence_section = md.split("## Evidence References")[1].split(
            "## TraceVault Metadata"
        )[0]
        assert evidence_section.count("### E1") == 1

    def test_rendered_evidence_preserves_richer_metadata(self):
        """B: Rendered evidence entry preserves richer metadata from
        source_evidence."""
        claim_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        source_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="abc123",
            evidence_text_hash="ghi789",
            excerpt="Full evidence text here",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[claim_ref])],
            source_evidence=[source_ref],
            metadata=meta,
        ))
        # Richer metadata must appear in rendered output
        assert "`docs/test.md`" in md
        assert "`abc123`" in md
        assert "`ghi789`" in md
        assert "> Full evidence text here" in md

    def test_claim_citation_points_to_canonical_label(self):
        """C: Claim citation points to the canonical display label for
        the single evidence entry."""
        claim_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        source_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc123",
            evidence_text_hash="def456",
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[claim_ref])],
            source_evidence=[source_ref],
            metadata=meta,
        ))
        # Claim line should cite E1 (canonical label)
        assert "A fact [E1]" in md

    def test_no_duplicate_evidence_headings_same_doc_chunk(self):
        """D: No duplicate evidence headings for same document_id/chunk_id."""
        ref1 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="abc",
        )
        ref2 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            # no hashes — sparse
        )
        meta = _make_validated_metadata(evidence_count=1)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        evidence_section = md.split("## Evidence References")[1].split(
            "## TraceVault Metadata"
        )[0]
        headings = [
            line for line in evidence_section.split("\n")
            if line.startswith("### ")
        ]
        assert len(headings) == len(set(headings))

    def test_same_label_different_chunk_distinct_entries(self):
        """E: Same label but different chunk_id still renders as distinct
        evidence entries with unique labels."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        assert _heading_exists(md, "### E1")
        assert _heading_exists(md, "### E1-2")

    def test_same_document_different_chunk_distinct(self):
        """F: Same document_id but different chunk_id remains distinct."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E2", document_id="doc_001", chunk_id="chunk_002"
        )
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        assert _heading_exists(md, "### E1")
        assert _heading_exists(md, "### E2")

    def test_identity_key_does_not_include_label(self):
        """G: identity_key does not include label when doc/chunk present."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="DIFFERENT", document_id="doc_001", chunk_id="chunk_001"
        )
        assert ref1.identity_key() == ref2.identity_key()

    def test_identity_key_does_not_split_on_hash_diff(self):
        """H: identity_key does not split on optional hash differences
        when document_id/chunk_id match."""
        ref1 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_raw_hash="hash_a",
            evidence_text_hash="hash_b",
        )
        ref2 = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            # no hashes
        )
        assert ref1.identity_key() == ref2.identity_key()

    def test_original_evidence_objects_not_mutated(self):
        """I: Original evidence objects are not mutated during render."""
        claim_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        source_ref = WikiEvidenceReference(
            label="E1",
            document_id="doc_001",
            chunk_id="chunk_001",
            source_path="docs/test.md",
            source_raw_hash="abc123",
            evidence_text_hash="def456",
            excerpt="Rich evidence",
        )
        # Snapshot original state
        claim_ref_before = claim_ref.to_dict()
        source_ref_before = source_ref.to_dict()

        meta = _make_validated_metadata(evidence_count=1)
        render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[claim_ref])],
            source_evidence=[source_ref],
            metadata=meta,
        ))

        # Neither object should be mutated
        assert claim_ref.to_dict() == claim_ref_before
        assert source_ref.to_dict() == source_ref_before


class TestGloballyUniqueEvidenceLabels:
    """Codex P1: evidence display labels must be globally unique across the
    entire note, not just unique per original-label group."""

    def test_duplicate_e1_plus_separate_original_e1_2(self):
        """A: Duplicate E1 plus separate original E1-2 produces unique labels."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="E1-2", document_id="doc_002", chunk_id="chunk_003"
        )
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        ))
        assert _heading_exists(md, "### E1")
        assert _heading_exists(md, "### E1-2")
        assert _heading_exists(md, "### E1-3")

    def test_claim_citation_tokens_point_to_final_labels(self):
        """B: Claim citation tokens point to final globally unique labels."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="E1-2", document_id="doc_002", chunk_id="chunk_003"
        )
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        ))
        # Citation tokens in the claim line must use the final unique labels
        assert "[E1, E1-3, E1-2]" in md

    def test_evidence_headings_are_unique(self):
        """C: Evidence headings are unique — no duplicate ### headings."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="E1-2", document_id="doc_002", chunk_id="chunk_003"
        )
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        ))
        evidence_section = md.split("## Evidence References")[1].split(
            "## TraceVault Metadata"
        )[0]
        headings = [
            line for line in evidence_section.split("\n")
            if line.startswith("### ")
        ]
        assert len(headings) == len(set(headings))

    def test_three_duplicates_same_label(self):
        """D: Three duplicates of same label produce E1, E1-2, E1-3."""
        refs = [
            WikiEvidenceReference(
                label="E1", document_id="doc_001", chunk_id=f"chunk_{i}"
            )
            for i in range(1, 4)
        ]
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=refs)],
            source_evidence=refs,
            metadata=meta,
        ))
        assert _heading_exists(md, "### E1")
        assert _heading_exists(md, "### E1-2")
        assert _heading_exists(md, "### E1-3")

    def test_e1_2_exists_duplicate_e1_skips_to_next(self):
        """E: If E1-2 already exists, duplicate E1 skips to next available."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1-2", document_id="doc_002", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_003"
        )
        meta = _make_validated_metadata(evidence_count=3)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        ))
        assert _heading_exists(md, "### E1")
        assert _heading_exists(md, "### E1-2")
        assert _heading_exists(md, "### E1-3")

    def test_existing_disambiguation_tests_still_pass(self):
        """F: Existing duplicate-label tests still work."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        meta = _make_validated_metadata(evidence_count=2)
        md = render_note(_make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        ))
        assert "E1" in md
        assert "E1-2" in md
        assert "[E1, E1-2]" in md

    def test_original_evidence_objects_not_mutated(self):
        """G: Original evidence reference objects are not mutated."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="E1-2", document_id="doc_002", chunk_id="chunk_003"
        )
        labels_before = [ref1.label, ref2.label, ref3.label]
        meta = _make_validated_metadata(evidence_count=3)
        render_note(_make_note(
            claims=[WikiClaim(statement="A", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        ))
        # Labels must not be mutated
        assert ref1.label == labels_before[0]
        assert ref2.label == labels_before[1]
        assert ref3.label == labels_before[2]


class TestMissingLabelFallbackRendering:
    """Codex P2: non-string/empty label rendering must not crash and must
    use a deterministic safe fallback display label."""

    def test_label_none_does_not_raise(self):
        """A: render_note with label=None does not raise TypeError."""
        ref = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        meta = _make_validated_metadata(evidence_count=1)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        )
        # Must not raise
        md = render_note(note)
        assert "# Test Note" in md

    def test_label_none_renders_fallback(self):
        """B: label=None renders a fallback label containing 'evidence'."""
        ref = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        meta = _make_validated_metadata(evidence_count=1)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        )
        md = render_note(note)
        assert "[evidence]" in md

    def test_label_empty_renders_fallback(self):
        """C: label="" renders fallback label."""
        ref = WikiEvidenceReference(
            label="", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = _make_validated_metadata(evidence_count=1)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        )
        md = render_note(note)
        assert "[evidence]" in md

    def test_label_whitespace_renders_fallback(self):
        """D: label="   " renders fallback label."""
        ref = WikiEvidenceReference(
            label="   ", document_id="doc_001", chunk_id="chunk_001"
        )
        meta = _make_validated_metadata(evidence_count=1)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        )
        md = render_note(note)
        assert "[evidence]" in md

    def test_multiple_missing_labels_unique_fallback(self):
        """E: Multiple missing labels render globally unique fallback labels."""
        ref1 = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        ref2 = WikiEvidenceReference(
            label="", document_id="doc_002", chunk_id="chunk_002"
        )
        ref3 = WikiEvidenceReference(
            label="  ", document_id="doc_003", chunk_id="chunk_003"
        )
        meta = _make_validated_metadata(evidence_count=3)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2, ref3])],
            source_evidence=[ref1, ref2, ref3],
            metadata=meta,
        )
        md = render_note(note)
        # All three should get unique fallback labels
        assert "evidence" in md
        assert "evidence-2" in md
        assert "evidence-3" in md

    def test_existing_evidence_label_plus_missing_no_collision(self):
        """F: existing label 'evidence' plus missing label does not collide."""
        ref_valid = WikiEvidenceReference(
            label="evidence", document_id="doc_001", chunk_id="chunk_001"
        )
        ref_missing = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_002",
            chunk_id="chunk_002",
        )
        meta = _make_validated_metadata(evidence_count=2)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref_valid, ref_missing])],
            source_evidence=[ref_valid, ref_missing],
            metadata=meta,
        )
        md = render_note(note)
        # Valid "evidence" label keeps its name, missing label gets disambiguated
        assert "### evidence" in md
        assert "evidence-2" in md

    def test_claim_citation_join_never_receives_non_string(self):
        """G: claim citation join never receives non-string labels."""
        ref1 = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        ref2 = WikiEvidenceReference(
            label="", document_id="doc_002", chunk_id="chunk_002"
        )
        meta = _make_validated_metadata(evidence_count=2)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        )
        # Must not raise TypeError from ", ".join()
        md = render_note(note)
        # The claim line should contain string citation labels
        claim_lines = [
            line for line in md.split("\n") if line.startswith("- A fact [")
        ]
        assert len(claim_lines) == 1
        # Verify all label tokens in brackets are non-empty strings
        bracket_content = claim_lines[0].split("[", 1)[1].split("]")[0]
        for token in bracket_content.split(", "):
            assert isinstance(token, str)
            assert token.strip()

    def test_original_evidence_ref_label_unchanged_after_render(self):
        """H: original evidence ref label remains None/unchanged after render."""
        ref = WikiEvidenceReference(
            label=None,  # type: ignore[arg-type]
            document_id="doc_001",
            chunk_id="chunk_001",
        )
        meta = _make_validated_metadata(evidence_count=1)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref])],
            source_evidence=[ref],
            metadata=meta,
        )
        render_note(note)
        # The original ref must not be mutated
        assert ref.label is None

    def test_valid_labels_still_render_unchanged(self):
        """I: Valid labels still render unchanged."""
        ref1 = WikiEvidenceReference(
            label="E1", document_id="doc_001", chunk_id="chunk_001"
        )
        ref2 = WikiEvidenceReference(
            label="E2", document_id="doc_002", chunk_id="chunk_002"
        )
        meta = _make_validated_metadata(evidence_count=2)
        note = _make_note(
            claims=[WikiClaim(statement="A fact", evidence_refs=[ref1, ref2])],
            source_evidence=[ref1, ref2],
            metadata=meta,
        )
        md = render_note(note)
        assert "[E1, E2]" in md
        assert "### E1" in md
        assert "### E2" in md


def _heading_exists(md: str, heading: str) -> bool:
    """Check if an exact heading line exists (not a substring of a longer heading)."""
    prefix = heading + " "
    for line in md.split("\n"):
        if line == heading or line.startswith(prefix):
            return True
    return False
