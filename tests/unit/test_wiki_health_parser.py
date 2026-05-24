"""Tests for wiki frontmatter parser (parser.py)."""

import textwrap
from pathlib import Path

import pytest

from tracevault.wiki.parser import (
    extract_frontmatter,
    parse_wiki_note,
    parse_yaml_frontmatter,
)


class TestExtractFrontmatter:
    def test_valid_frontmatter(self):
        md = "---\nkey: value\n---\n\n# Body"
        fm, body = extract_frontmatter(md)
        assert fm == "key: value"
        assert body.strip() == "# Body"

    def test_no_frontmatter(self):
        md = "# No Frontmatter\n\nBody"
        fm, body = extract_frontmatter(md)
        assert fm is None
        assert body == md

    def test_malformed_no_closing(self):
        md = "---\nkey: value\n# Body"
        fm, body = extract_frontmatter(md)
        assert fm == "MALFORMED"

    def test_empty_frontmatter(self):
        md = "---\n---\n# Body"
        fm, body = extract_frontmatter(md)
        assert fm == ""
        assert body.strip() == "# Body"

    def test_multiline_frontmatter(self):
        md = "---\nkey1: val1\nkey2: val2\n---\n\nBody"
        fm, body = extract_frontmatter(md)
        assert "key1: val1" in fm
        assert "key2: val2" in fm

    def test_leading_newlines(self):
        md = "\n\n---\nkey: val\n---\nBody"
        fm, body = extract_frontmatter(md)
        assert fm == "key: val"


class TestParseYamlFrontmatter:
    def test_simple_key_value(self):
        result = parse_yaml_frontmatter('key: "value"')
        assert result == {"key": "value"}

    def test_multiple_keys(self):
        result = parse_yaml_frontmatter('a: "1"\nb: "2"')
        assert result == {"a": "1", "b": "2"}

    def test_integer_value(self):
        result = parse_yaml_frontmatter("count: 42")
        assert result == {"count": 42}

    def test_boolean_value(self):
        result = parse_yaml_frontmatter("flag: true")
        assert result == {"flag": True}

    def test_null_value(self):
        result = parse_yaml_frontmatter("val: null")
        assert result == {"val": None}

    def test_escaped_string(self):
        result = parse_yaml_frontmatter(r'val: "hello\nworld"')
        assert result == {"val": "hello\nworld"}

    def test_empty_string(self):
        result = parse_yaml_frontmatter('val: ""')
        assert result == {"val": ""}

    def test_mixed_types(self):
        result = parse_yaml_frontmatter(
            'note_id: "note_001"\nevidence_count: 3\nflag: true'
        )
        assert result == {"note_id": "note_001", "evidence_count": 3, "flag": True}


class TestParseWikiNote:
    def _write_note(self, tmp_path: Path, content: str, name: str = "note.md") -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_note(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            evidence_count: 1
            ---

            # Test Note

            ## Claims

            - A fact [E1]

            ## Evidence References

            ### E1

            - **Document**: `doc_001`
            - **Chunk**: `chunk_001`

            ---

            ## TraceVault Metadata

            - note_id: `note_001`
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.frontmatter["note_id"] == "note_001"
        assert parsed.frontmatter["evidence_count"] == 1
        assert "E1" in parsed.evidence_labels
        assert "A fact" in parsed.claim_citations
        assert parsed.claim_citations["A fact"] == ["E1"]

    def test_no_frontmatter(self, tmp_path: Path):
        content = "# No Frontmatter\n\nBody text."
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.frontmatter == {}
        assert parsed.raw_frontmatter == ""
        assert parsed.body == content

    def test_malformed_frontmatter(self, tmp_path: Path):
        content = "---\nkey: value\n# No closing"
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.frontmatter == {}

    def test_evidence_labels_extracted(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: "n1"
            ---

            ## Evidence References

            ### E1

            - **Document**: `doc_001`

            ### E2

            - **Document**: `doc_002`
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.evidence_labels == ["E1", "E2"]

    def test_claim_citations_extracted(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: "n1"
            ---

            ## Claims

            - First claim [E1]
            - Second claim [E2, E3]
            - Unsupported claim *(unsupported — no evidence)*
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.claim_citations["First claim"] == ["E1"]
        assert parsed.claim_citations["Second claim"] == ["E2", "E3"]
        # Unsupported claims are not in claim_citations (no bracket pattern)
        assert "Unsupported claim" not in parsed.claim_citations

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_wiki_note(tmp_path / "nonexistent.md")

    def test_body_preserved(self, tmp_path: Path):
        content = "---\nnote_id: \"n1\"\n---\n\n# Title\n\nBody paragraph."
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert "# Title" in parsed.body
        assert "Body paragraph" in parsed.body


class TestMalformedYAMLFailClosed:
    """Regression tests: malformed YAML must fail closed, not traceback."""

    def _write_note(self, tmp_path: Path, content: str, name: str = "note.md") -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_unterminated_bracket_in_yaml(self, tmp_path: Path):
        """YAML like 'note_id: [unterminated' must not crash."""
        content = textwrap.dedent('''\
            ---
            note_id: [unterminated
            ---
            # Bad
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        # Must not crash; frontmatter should be empty
        assert parsed.frontmatter == {}
        assert parsed.yaml_parse_error is True

    def test_malformed_yaml_sets_parse_error_flag(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            key: :invalid: yaml: [
            ---
            # Body
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.yaml_parse_error is True
        assert parsed.frontmatter == {}

    def test_malformed_yaml_still_extracts_body(self, tmp_path: Path):
        """Body after the closing --- should still be extracted."""
        content = textwrap.dedent('''\
            ---
            note_id: [broken
            ---

            # My Title

            Body text here.
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.yaml_parse_error is True
        assert "# My Title" in parsed.body
        assert "Body text here" in parsed.body

    def test_valid_yaml_no_parse_error(self, tmp_path: Path):
        content = textwrap.dedent('''\
            ---
            note_id: "n1"
            evidence_count: 1
            ---
            # OK
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.yaml_parse_error is False
        assert parsed.frontmatter["note_id"] == "n1"

    def test_no_frontmatter_no_parse_error(self, tmp_path: Path):
        content = "# No frontmatter"
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.yaml_parse_error is False
        assert parsed.frontmatter == {}

    def test_nested_source_documents_parses(self, tmp_path: Path):
        """Phase 6A-style nested frontmatter with source_documents must parse."""
        content = textwrap.dedent('''\
            ---
            note_id: "note_001"
            note_type: "compiled_knowledge_wiki_note"
            evidence_count: 1
            source_documents:
              - document_id: doc_001
                source_path: docs/test.md
                source_raw_hash: abc123
                content_hash: abc123
            source_chunks:
              - chunk_id: chunk_001
                document_id: doc_001
            ---
            # OK
        ''')
        parsed = parse_wiki_note(self._write_note(tmp_path, content))
        assert parsed.yaml_parse_error is False
        assert parsed.frontmatter["note_id"] == "note_001"
        assert isinstance(parsed.frontmatter["source_documents"], list)
        assert len(parsed.frontmatter["source_documents"]) == 1
        assert parsed.frontmatter["source_documents"][0]["document_id"] == "doc_001"
        assert parsed.frontmatter["source_documents"][0]["source_raw_hash"] == "abc123"
        assert parsed.frontmatter["source_documents"][0]["content_hash"] == "abc123"
