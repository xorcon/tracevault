"""Tests for rule-based refiner and no-new-facts safeguard."""

from tracevault.refinement.refiner import (
    check_no_new_facts,
    rule_based_refine,
)


class TestRuleBasedRefiner:
    """Tests for rule_based_refine function."""

    def test_trims_leading_trailing_whitespace(self):
        """Whitespace is trimmed from start and end."""
        text = "  Hello world  "
        cleaned, _ = rule_based_refine(text)
        assert cleaned == "Hello world"

    def test_normalizes_excessive_blank_lines(self):
        """Three or more blank lines become two."""
        text = "Line1\n\n\n\nLine2"
        cleaned, _ = rule_based_refine(text)
        assert "\n\n\n" not in cleaned  # No triple newlines
        assert "Line1" in cleaned and "Line2" in cleaned

    def test_normalizes_repeated_spaces(self):
        """Multiple spaces become single space."""
        text = "Hello   world"
        cleaned, _ = rule_based_refine(text)
        assert "   " not in cleaned  # No triple spaces
        assert cleaned == "Hello world"

    def test_preserves_markdown_headings(self):
        """Markdown headings are preserved."""
        text = "# Heading\n## Subheading"
        cleaned, _ = rule_based_refine(text)
        assert "# Heading" in cleaned
        assert "## Subheading" in cleaned

    def test_does_not_add_text(self):
        """Refiner does not add new words."""
        text = "The project uses Python."
        cleaned, _ = rule_based_refine(text)
        # Check no obvious additions
        assert "Java" not in cleaned
        assert "JavaScript" not in cleaned

    def test_does_not_modify_numbers(self):
        """Numbers are preserved exactly."""
        text = "Version 2.3.1 released on 2024-01-15. Cost: $1,234.56"
        cleaned, _ = rule_based_refine(text)
        assert "2.3.1" in cleaned
        assert "2024-01-15" in cleaned
        assert "1,234.56" in cleaned or "1234.56" in cleaned

    def test_does_not_modify_names(self):
        """Names and identifiers are preserved."""
        text = "User xorcon deployed to prod-us-east-1"
        cleaned, _ = rule_based_refine(text)
        assert "xorcon" in cleaned
        assert "prod-us-east-1" in cleaned

    def test_handles_empty_input(self):
        """Empty input returns empty string."""
        cleaned, meta = rule_based_refine("")
        assert cleaned == ""
        assert meta.refinement_method == "rule_based"

    def test_produces_metadata(self):
        """Metadata is produced with correct fields."""
        text = "Test text"
        cleaned, meta = rule_based_refine(text)
        assert meta.refinement_method == "rule_based"
        assert meta.model_name is None
        assert meta.no_new_facts_checked is True
        assert meta.prompt_version == "v1.0"

    def test_preserves_factual_content(self):
        """Factual content is not deleted."""
        text = "The server crashed at 03:42 UTC due to OOM. Process: nginx."
        cleaned, _ = rule_based_refine(text)
        assert "03:42" in cleaned
        assert "OOM" in cleaned
        assert "nginx" in cleaned


class TestNoNewFactsSafeguard:
    """Tests for check_no_new_facts function."""

    def test_detects_added_words(self):
        """Words in cleaned but not raw are flagged."""
        raw = "The server crashed."
        cleaned = "The server crashed due to memory issues."
        warnings = check_no_new_facts(raw, cleaned)
        assert "memory" in warnings.added_words or "issues" in warnings.added_words

    def test_detects_added_numbers(self):
        """Numbers in cleaned but not raw are flagged."""
        raw = "The version is old."
        cleaned = "The version is 2.5."
        warnings = check_no_new_facts(raw, cleaned)
        assert "2.5" in warnings.added_numbers or "2" in warnings.added_numbers

    def test_detects_empty_cleaned_from_nonempty_raw(self):
        """Empty cleaned text from non-empty raw is flagged."""
        raw = "Some text"
        cleaned = ""
        warnings = check_no_new_facts(raw, cleaned)
        assert warnings.empty_cleaned is True

    def test_allows_safe_whitespace_normalization(self):
        """Whitespace normalization does not trigger warnings."""
        raw = "  Hello   world  "
        cleaned = "Hello world"
        warnings = check_no_new_facts(raw, cleaned)
        # Should not flag whitespace changes as added words
        assert len(warnings.added_words) == 0

    def test_no_warnings_for_identical_text(self):
        """Identical text produces no warnings."""
        text = "Hello world"
        warnings = check_no_new_facts(text, text)
        assert len(warnings.added_words) == 0
        assert len(warnings.added_numbers) == 0
        assert warnings.empty_cleaned is False

    def test_empty_raw_returns_empty_warnings(self):
        """Empty raw text returns empty warnings."""
        warnings = check_no_new_facts("", "")
        assert warnings.added_words == []
        assert warnings.empty_cleaned is False

    def test_filters_stop_words(self):
        """Common stop words are not flagged as added."""
        raw = "Hello"
        cleaned = "Hello is good"
        warnings = check_no_new_facts(raw, cleaned)
        # "is" should be filtered as stop word
        assert "is" not in warnings.added_words
