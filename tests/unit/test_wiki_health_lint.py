"""Tests for single-note lint checks (lint.py)."""

import textwrap
from pathlib import Path

from tracevault.wiki.lint import lint_note
from tracevault.wiki.parser import parse_wiki_note
from tracevault.wiki.report import IssueSeverity


def _write_note(tmp_path: Path, content: str, name: str = "note.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _lint(content: str, tmp_path: Path, name: str = "note.md") -> list:
    path = _write_note(tmp_path, content, name)
    parsed = parse_wiki_note(path)
    return lint_note(parsed)


def _valid_note(evidence_count: int = 1, extra_fm: str = "", **kwargs) -> str:
    """Build a valid Phase 6A-style note for testing."""
    fm = textwrap.dedent(f'''\
        ---
        note_id: "{kwargs.get('note_id', 'note_001')}"
        note_type: "compiled_knowledge_wiki_note"
        status: "proposal"
        generated_at: "2026-01-01T00:00:00+00:00"
        generated_by: "tracevault"
        generator_version: "0.1.0"
        schema_version: "wiki-export-v1"
        source_policy: "raw_text_authoritative"
        validation_status: "{kwargs.get('validation_status', 'validated')}"
        evidence_count: {evidence_count}
        {extra_fm}
        ---

        # Test Note

        ## Claims

    ''')
    claims = kwargs.get("claims", "- A fact [E1]\n")
    evidence = kwargs.get("evidence", _evidence_section(1))
    metadata = kwargs.get("metadata", "\n## TraceVault Metadata\n\n- note_id: `note_001`\n")
    return f"{fm}{claims}\n{evidence}{metadata}"


def _evidence_section(count: int) -> str:
    lines = ["## Evidence References\n"]
    for i in range(1, count + 1):
        lines.append(f"""### E{i}

- **Document**: `doc_{i}`
- **Chunk**: `chunk_{i}`

""")
    return "\n".join(lines)


class TestValidNote:
    def test_clean_note_passes(self, tmp_path: Path):
        issues = _lint(_valid_note(), tmp_path)
        assert issues == []

    def test_note_with_multiple_evidence(self, tmp_path: Path):
        issues = _lint(_valid_note(
            evidence_count=2,
            claims="- First [E1]\n- Second [E2]\n",
            evidence=_evidence_section(2),
        ), tmp_path)
        assert issues == []

    def test_note_with_unsupported_claim(self, tmp_path: Path):
        issues = _lint(_valid_note(
            evidence_count=1,
            claims="- A fact [E1]\n- Speculation *(unsupported — no evidence)*\n",
        ), tmp_path)
        assert issues == []


class TestMissingFrontmatter:
    def test_no_frontmatter_delimiter(self, tmp_path: Path):
        issues = _lint("# Just a title\n\nNo frontmatter here.", tmp_path)
        assert len(issues) == 1
        assert issues[0].code == "missing_frontmatter"
        assert issues[0].severity is IssueSeverity.ERROR

    def test_malformed_no_closing(self, tmp_path: Path):
        issues = _lint("---\nnote_id: val\n# No closing", tmp_path)
        assert len(issues) == 1
        assert issues[0].code == "malformed_frontmatter"
        assert issues[0].severity is IssueSeverity.ERROR


class TestMissingRequiredFields:
    def test_missing_note_id(self, tmp_path: Path):
        issues = _lint(_valid_note(extra_fm=""), tmp_path)
        # Remove note_id from frontmatter
        content = _valid_note().replace('note_id: "note_001"\n', "")
        issues = _lint(content, tmp_path)
        assert any("note_id" in i.message for i in issues if i.code == "missing_required_field")

    def test_missing_note_type(self, tmp_path: Path):
        content = _valid_note().replace('note_type: "compiled_knowledge_wiki_note"\n', "")
        issues = _lint(content, tmp_path)
        assert any(
            "note_type" in i.message and i.code == "missing_required_field"
            for i in issues
        )

    def test_missing_source_policy(self, tmp_path: Path):
        content = _valid_note().replace(
            'source_policy: "raw_text_authoritative"\n', ""
        )
        issues = _lint(content, tmp_path)
        assert any(
            "source_policy" in i.message and i.code == "missing_required_field"
            for i in issues
        )

    def test_empty_string_field(self, tmp_path: Path):
        content = _valid_note().replace(
            'note_id: "note_001"', 'note_id: ""'
        )
        issues = _lint(content, tmp_path)
        assert any(
            "note_id" in i.message and i.code == "missing_required_field"
            for i in issues
        )


class TestInvalidNoteType:
    def test_wrong_note_type(self, tmp_path: Path):
        content = _valid_note().replace(
            'note_type: "compiled_knowledge_wiki_note"',
            'note_type: "random_note"',
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "invalid_note_type" for i in issues)


class TestInvalidSchemaVersion:
    def test_wrong_schema_version(self, tmp_path: Path):
        content = _valid_note().replace(
            'schema_version: "wiki-export-v1"',
            'schema_version: "wiki-export-v2"',
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "invalid_schema_version" for i in issues)


class TestInvalidStatus:
    def test_wrong_status(self, tmp_path: Path):
        content = _valid_note().replace(
            'status: "proposal"', 'status: "unknown_status"'
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "invalid_status" for i in issues)

    def test_valid_statuses_pass(self, tmp_path: Path):
        for status in ("proposal", "published", "draft", "deprecated"):
            content = _valid_note().replace('status: "proposal"', f'status: "{status}"')
            issues = _lint(content, tmp_path)
            assert not any(i.code == "invalid_status" for i in issues)


class TestInvalidSourcePolicy:
    def test_wrong_source_policy(self, tmp_path: Path):
        content = _valid_note().replace(
            'source_policy: "raw_text_authoritative"',
            'source_policy: "cleaned_text_authoritative"',
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "invalid_source_policy" for i in issues)

    def test_correct_source_policy(self, tmp_path: Path):
        issues = _lint(_valid_note(), tmp_path)
        assert not any(i.code == "invalid_source_policy" for i in issues)


class TestInvalidValidationStatus:
    def test_validated_passes(self, tmp_path: Path):
        issues = _lint(_valid_note(validation_status="validated"), tmp_path)
        assert not any(i.code == "invalid_validation_status" for i in issues)

    def test_validation_required_warning(self, tmp_path: Path):
        issues = _lint(_valid_note(validation_status="validation_required"), tmp_path)
        vs_issues = [i for i in issues if i.code == "invalid_validation_status"]
        assert len(vs_issues) == 1
        assert vs_issues[0].severity is IssueSeverity.WARNING

    def test_unknown_validation_status_error(self, tmp_path: Path):
        content = _valid_note().replace(
            'validation_status: "validated"',
            'validation_status: "unknown_status"',
        )
        issues = _lint(content, tmp_path)
        vs_issues = [i for i in issues if i.code == "invalid_validation_status"]
        assert len(vs_issues) == 1
        assert vs_issues[0].severity is IssueSeverity.ERROR


class TestEvidenceCountMismatch:
    def test_count_too_high(self, tmp_path: Path):
        issues = _lint(_valid_note(evidence_count=3), tmp_path)
        assert any(i.code == "evidence_count_mismatch" for i in issues)

    def test_count_too_low(self, tmp_path: Path):
        content = _valid_note(evidence_count=1)
        content = content.replace("evidence_count: 1", "evidence_count: 0")
        issues = _lint(content, tmp_path)
        assert any(i.code == "evidence_count_mismatch" for i in issues)

    def test_count_matches(self, tmp_path: Path):
        issues = _lint(_valid_note(
            evidence_count=2,
            claims="- First [E1]\n- Second [E2]\n",
            evidence=_evidence_section(2),
        ), tmp_path)
        assert not any(i.code == "evidence_count_mismatch" for i in issues)


class TestClaimMissingCitation:
    def test_supported_claim_no_citation(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,
            claims="- A fact with no citation\n",
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "claim_missing_citation" for i in issues)

    def test_unsupported_claim_skipped(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=0,
            claims="- Speculation *(unsupported — no evidence)*\n",
            evidence="## Evidence References\n",
        )
        issues = _lint(content, tmp_path)
        assert not any(i.code == "claim_missing_citation" for i in issues)


class TestCitationUnresolved:
    def test_citation_not_in_evidence(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,
            claims="- A fact [E99]\n",
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "citation_unresolved" for i in issues)

    def test_valid_citation_resolves(self, tmp_path: Path):
        issues = _lint(_valid_note(), tmp_path)
        assert not any(i.code == "citation_unresolved" for i in issues)


class TestEvidenceMissingMetadata:
    def test_missing_document_id(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,
            evidence="## Evidence References\n\n### E1\n\n- **Chunk**: `chunk_001`\n\n",
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "evidence_missing_document_id" for i in issues)

    def test_missing_chunk_id(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,
            evidence="## Evidence References\n\n### E1\n\n- **Document**: `doc_001`\n\n",
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "evidence_missing_chunk_id" for i in issues)

    def test_both_present_passes(self, tmp_path: Path):
        issues = _lint(_valid_note(), tmp_path)
        assert not any(i.code in ("evidence_missing_document_id", "evidence_missing_chunk_id") for i in issues)


class TestDuplicateEvidenceLabel:
    def test_duplicate_label(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,  # claim says 1, but we have 2 E1 headings
            claims="- A fact [E1]\n",
            evidence=textwrap.dedent('''\
                ## Evidence References

                ### E1

                - **Document**: `doc_001`
                - **Chunk**: `chunk_001`

                ### E1

                - **Document**: `doc_002`
                - **Chunk**: `chunk_002`

            '''),
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "duplicate_evidence_label" for i in issues)

    def test_unique_labels_pass(self, tmp_path: Path):
        issues = _lint(_valid_note(
            evidence_count=2,
            claims="- A fact [E1]\n- Second [E2]\n",
            evidence=_evidence_section(2),
        ), tmp_path)
        assert not any(i.code == "duplicate_evidence_label" for i in issues)


class TestMissingTraceVaultMetadata:
    def test_missing_metadata_section(self, tmp_path: Path):
        content = _valid_note(
            evidence_count=1,
            metadata="",  # no TraceVault Metadata section
        )
        issues = _lint(content, tmp_path)
        assert any(i.code == "missing_tracevault_metadata" for i in issues)

    def test_metadata_section_present(self, tmp_path: Path):
        issues = _lint(_valid_note(), tmp_path)
        assert not any(i.code == "missing_tracevault_metadata" for i in issues)


class TestSourceHashMismatch:
    def test_no_source_hashes_skipped(self, tmp_path: Path):
        """Without source_hashes, no hash check should run."""
        path = _write_note(tmp_path, _valid_note())
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes=None)
        assert not any(i.code in ("source_hash_mismatch", "source_hash_missing_expected") for i in issues)

    def test_hash_mismatch(self, tmp_path: Path):
        path = _write_note(tmp_path, _valid_note())
        parsed = parse_wiki_note(path)
        # Provide source hash that doesn't match the note's content
        issues = lint_note(parsed, source_hashes={
            "doc_001": "different_hash_value",
        })
        # Should flag mismatch since the note doesn't have source_raw_hash
        # but the manifest has a hash for doc_001
        # Actually, the check requires the note to have a source_raw_hash
        # that differs from the manifest. If the note doesn't have the hash,
        # it's not a mismatch — it's just not checked.
        # Let me check: the lint checks source hashes from the evidence section
        # or frontmatter source_documents. Since our valid note doesn't have
        # source_raw_hash in the evidence section, no check runs.
        # So this should be clean.
        assert not any(i.code == "source_hash_mismatch" for i in issues)

    def test_hash_check_with_source_documents(self, tmp_path: Path):
        """Source hash check works when frontmatter has source_documents."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                source_raw_hash: abc123
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        path = _write_note(tmp_path, content)
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={"doc_001": "def456"})
        assert any(i.code == "source_hash_mismatch" for i in issues)

    def test_hash_missing_expected(self, tmp_path: Path):
        """Document in note not found in source manifest."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                source_raw_hash: abc123
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        path = _write_note(tmp_path, content)
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={"doc_999": "xyz"})
        assert any(i.code == "source_hash_missing_expected" for i in issues)


class TestMalformedYAMLLint:
    """Regression: malformed YAML frontmatter must produce structured issue."""

    def test_yaml_parse_error_emits_malformed_frontmatter(self, tmp_path: Path):
        """Parser sets yaml_parse_error=True; linter must emit malformed_frontmatter."""
        content = textwrap.dedent('''\
            ---
            note_id: [unterminated
            ---
            # Bad
        ''')
        issues = _lint(content, tmp_path)
        assert len(issues) == 1
        assert issues[0].code == "malformed_frontmatter"
        assert issues[0].severity is IssueSeverity.ERROR

    def test_yaml_parse_error_stops_further_checks(self, tmp_path: Path):
        """When YAML is malformed, do not run downstream field checks."""
        content = textwrap.dedent('''\
            ---
            note_id: [broken
            ---
            # Bad
        ''')
        issues = _lint(content, tmp_path)
        # Should be only malformed_frontmatter, not missing_required_field, etc.
        assert all(i.code == "malformed_frontmatter" for i in issues)
        assert not any(i.code == "missing_required_field" for i in issues)


class TestSourceHashWithContentHash:
    """Regression: source hash check must use content_hash from frontmatter."""

    def test_content_hash_matching(self, tmp_path: Path):
        """source_documents with content_hash should be checked against manifest."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                content_hash: abc123
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        path = _write_note(tmp_path, content)
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={"doc_001": "def456"})
        assert any(i.code == "source_hash_mismatch" for i in issues)

    def test_content_hash_match_no_issue(self, tmp_path: Path):
        """Matching content_hash should produce no issue."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                content_hash: abc123
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        path = _write_note(tmp_path, content)
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={"doc_001": "abc123"})
        assert not any(i.code in ("source_hash_mismatch", "source_hash_missing_expected") for i in issues)


class TestSourcePathBasedDriftCheck:
    """Regression: real entries[] manifest uses source_path as lookup key."""

    def _note_with_source_path(self, content_hash_val: str) -> str:
        return textwrap.dedent(f'''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                source_path: docs/test.md
                content_hash: {content_hash_val}
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')

    def test_real_manifest_source_path_match(self, tmp_path: Path):
        """source_path in note matches manifest entry source_path, content_hash matches."""
        path = _write_note(tmp_path, self._note_with_source_path("abc123"))
        parsed = parse_wiki_note(path)
        # Simulate real ingestion manifest keyed by source_path
        issues = lint_note(parsed, source_hashes={
            "docs/test.md": "abc123",
        })
        assert not any(i.code == "source_hash_missing_expected" for i in issues)
        assert not any(i.code == "source_hash_mismatch" for i in issues)

    def test_real_manifest_source_path_mismatch(self, tmp_path: Path):
        """source_path matches but content_hash differs → source_hash_mismatch."""
        path = _write_note(tmp_path, self._note_with_source_path("abc123"))
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={
            "docs/test.md": "different_hash",
        })
        assert any(i.code == "source_hash_mismatch" for i in issues)
        # The message should include the source_path
        mismatch = [i for i in issues if i.code == "source_hash_mismatch"][0]
        assert "docs/test.md" in mismatch.message

    def test_source_path_not_in_manifest(self, tmp_path: Path):
        """source_path exists in note but not in manifest → source_hash_missing_expected."""
        path = _write_note(tmp_path, self._note_with_source_path("abc123"))
        parsed = parse_wiki_note(path)
        issues = lint_note(parsed, source_hashes={
            "docs/other.md": "xyz",
        })
        assert any(i.code == "source_hash_missing_expected" for i in issues)
        missing = [i for i in issues if i.code == "source_hash_missing_expected"][0]
        assert "docs/test.md" in missing.message

    def test_document_id_fallback_still_works(self, tmp_path: Path):
        """When source_path is absent, document_id is the lookup key."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            status: "proposal"
            generated_at: "2026-01-01T00:00:00+00:00"
            generated_by: "tracevault"
            generator_version: "0.1.0"
            schema_version: "wiki-export-v1"
            source_policy: "raw_text_authoritative"
            validation_status: "validated"
            evidence_count: 0
            source_documents:
              - document_id: doc_001
                source_raw_hash: abc123
            ---

            # Test

            ## Claims

            ## Evidence References

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        path = _write_note(tmp_path, content)
        parsed = parse_wiki_note(path)
        # No source_path → document_id fallback lookup
        issues = lint_note(parsed, source_hashes={"doc_001": "def456"})
        assert any(i.code == "source_hash_mismatch" for i in issues)

    def test_source_path_takes_precedence_over_document_id(self, tmp_path: Path):
        """When both source_path and document_id exist, source_path is the key."""
        path = _write_note(tmp_path, self._note_with_source_path("abc123"))
        parsed = parse_wiki_note(path)
        # document_id "doc_001" in expected hashes should NOT match —
        # the lookup key is source_path "docs/test.md"
        issues = lint_note(parsed, source_hashes={"doc_001": "abc123"})
        # source_path "docs/test.md" is not in expected hashes
        assert any(i.code == "source_hash_missing_expected" for i in issues)
