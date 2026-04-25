"""Unit tests for configuration settings.

Tests the Settings dataclass and environment variable loading.
"""

import os
import pytest
from pathlib import Path

from tracevault.config.settings import Settings, get_settings, reload_settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.data_dir == Path("./data")
        assert settings.log_level == "INFO"
        assert settings.model_provider == "local"
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200
        assert settings.top_k == 5
        assert settings.hybrid_alpha == 0.5
        assert settings.min_confidence_threshold == 0.7

    def test_from_env(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("TRACEVAULT_DATA_DIR", "/custom/data")
        monkeypatch.setenv("TRACEVAULT_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("TRACEVAULT_MODEL_PROVIDER", "ollama")
        monkeypatch.setenv("TRACEVAULT_CHUNK_SIZE", "2000")
        monkeypatch.setenv("TRACEVAULT_TOP_K", "10")
        monkeypatch.setenv("TRACEVAULT_HYBRID_ALPHA", "0.7")

        settings = Settings.from_env()

        assert settings.data_dir == Path("/custom/data")
        assert settings.log_level == "DEBUG"
        assert settings.model_provider == "ollama"
        assert settings.chunk_size == 2000
        assert settings.top_k == 10
        assert settings.hybrid_alpha == 0.7

    def test_validate_valid_settings(self):
        """Test validation with valid settings."""
        settings = Settings()
        errors = settings.validate()
        assert errors == []

    def test_validate_invalid_log_level(self):
        """Test validation catches invalid log level."""
        settings = Settings(log_level="INVALID")
        errors = settings.validate()
        assert any("log_level" in e for e in errors)

    def test_validate_invalid_hybrid_alpha(self):
        """Test validation catches invalid hybrid_alpha."""
        settings = Settings(hybrid_alpha=1.5)
        errors = settings.validate()
        assert any("hybrid_alpha" in e for e in errors)

    def test_validate_chunk_overlap_greater_than_size(self):
        """Test validation catches chunk_overlap >= chunk_size."""
        settings = Settings(chunk_size=500, chunk_overlap=600)
        errors = settings.validate()
        assert any("chunk_overlap" in e for e in errors)

    def test_get_settings_singleton(self):
        """Test that get_settings returns singleton."""
        # Reset module state
        import tracevault.config.settings as settings_module
        settings_module._settings = None

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reload_settings(self):
        """Test that reload_settings creates new instance."""
        import tracevault.config.settings as settings_module
        settings_module._settings = None

        s1 = get_settings()
        s2 = reload_settings()
        assert s1 is not s2


class TestSettingsIntegration:
    """Integration tests for settings."""

    def test_settings_with_custom_paths(self, tmp_path):
        """Test settings with temporary directory."""
        # tmp_path fixture creates the directory, so we create a non-existent subpath
        custom_path = tmp_path / "nonexistent" / "subdir"
        settings = Settings(data_dir=custom_path)
        assert settings.data_dir == custom_path
        assert not custom_path.exists()

        # Validate should not create directory
        errors = settings.validate()
        assert errors == []
