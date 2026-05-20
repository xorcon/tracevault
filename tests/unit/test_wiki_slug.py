"""Tests for deterministic wiki slug generation."""

from tracevault.wiki.slug import generate_slug


class TestGenerateSlugDeterministic:
    def test_same_input_same_output(self):
        assert generate_slug("My Title") == generate_slug("My Title")

    def test_different_input_different_output(self):
        assert generate_slug("Alpha") != generate_slug("Beta")


class TestGenerateSlugBasic:
    def test_simple_title(self):
        assert generate_slug("My Title") == "my-title"

    def test_lowercase_passthrough(self):
        assert generate_slug("already-lower") == "already-lower"

    def test_uppercase_converted(self):
        assert generate_slug("UPPER CASE") == "upper-case"

    def test_numbers_preserved(self):
        assert generate_slug("Section 3 of 5") == "section-3-of-5"


class TestGenerateSlugSpecialChars:
    def test_special_chars_replaced(self):
        assert generate_slug("Hello! World?") == "hello-world"

    def test_multiple_spaces_collapsed(self):
        assert generate_slug("Multiple   Spaces") == "multiple-spaces"

    def test_leading_trailing_spaces(self):
        assert generate_slug("  Trimmed  ") == "trimmed"

    def test_unicode_non_ascii_stripped(self):
        slug = generate_slug("Résumé")
        assert slug == "r-sum"

    def test_ampersand_replaced(self):
        assert generate_slug("A & B: The Story") == "a-b-the-story"


class TestGenerateSlugEdgeCases:
    def test_empty_string(self):
        assert generate_slug("") == "note"

    def test_only_special_chars(self):
        assert generate_slug("!!!") == "note"

    def test_only_spaces(self):
        assert generate_slug("   ") == "note"

    def test_single_word(self):
        assert generate_slug("Single") == "single"

    def test_leading_hyphen_in_title(self):
        assert generate_slug("- Leading Hyphen") == "leading-hyphen"
