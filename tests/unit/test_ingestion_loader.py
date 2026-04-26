"""Tests for file loader."""


import pytest

from tracevault.ingestion.loader import (
    SUPPORTED_EXTENSIONS,
    get_source_type,
    is_supported_file,
    load_file,
)


class TestLoader:
    """Test file loading utilities."""

    def test_supported_extensions(self):
        """Check supported extensions set."""
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".markdown" in SUPPORTED_EXTENSIONS
        assert ".pdf" not in SUPPORTED_EXTENSIONS

    def test_is_supported_file_txt(self, tmp_path):
        """Recognizes .txt files."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        assert is_supported_file(file_path) is True

    def test_is_supported_file_md(self, tmp_path):
        """Recognizes .md files."""
        file_path = tmp_path / "test.md"
        file_path.touch()
        assert is_supported_file(file_path) is True

    def test_is_supported_file_markdown(self, tmp_path):
        """Recognizes .markdown files."""
        file_path = tmp_path / "test.markdown"
        file_path.touch()
        assert is_supported_file(file_path) is True

    def test_is_supported_file_unsupported(self, tmp_path):
        """Rejects unsupported extensions."""
        for ext in [".pdf", ".docx", ".html", ".jpg", ""]:
            file_path = tmp_path / f"test{ext}"
            file_path.touch()
            assert is_supported_file(file_path) is False

    def test_load_file_preserves_raw_text(self, tmp_path):
        """Raw text is preserved exactly."""
        content = """# Header

Some text with   multiple   spaces.

- List item 1
- List item 2

> Quote here

`code block`
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content, encoding="utf-8")

        loaded, size = load_file(file_path)
        assert loaded == content
        assert size == len(content.encode("utf-8"))

    def test_load_file_unicode(self, tmp_path):
        """Handles unicode content."""
        content = "こんにちは世界\nHello World\nمرحبا بالعالم"
        file_path = tmp_path / "unicode.txt"
        file_path.write_text(content, encoding="utf-8")

        loaded, _ = load_file(file_path)
        assert loaded == content

    def test_load_file_missing(self, tmp_path):
        """Raises FileNotFoundError for missing file."""
        file_path = tmp_path / "missing.txt"
        with pytest.raises(FileNotFoundError):
            load_file(file_path)

    def test_load_file_is_directory(self, tmp_path):
        """Raises IsADirectoryError for directory."""
        with pytest.raises(IsADirectoryError):
            load_file(tmp_path)

    def test_get_source_type_md(self, tmp_path):
        """Returns 'md' for .md files."""
        file_path = tmp_path / "test.md"
        assert get_source_type(file_path) == "md"

    def test_get_source_type_markdown(self, tmp_path):
        """Returns 'md' for .markdown files."""
        file_path = tmp_path / "test.markdown"
        assert get_source_type(file_path) == "md"

    def test_get_source_type_txt(self, tmp_path):
        """Returns 'txt' for .txt files."""
        file_path = tmp_path / "test.txt"
        assert get_source_type(file_path) == "txt"
