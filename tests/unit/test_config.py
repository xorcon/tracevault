"""Unit tests for configuration settings.

Tests the Settings dataclass and environment variable loading.
"""

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


class TestMalformedEnvHandling:
    """Test graceful handling of malformed environment variables."""

    def test_malformed_int_chunk_size(self, monkeypatch):
        """Test malformed int for chunk_size uses default and reports error."""
        monkeypatch.setenv("TRACEVAULT_CHUNK_SIZE", "abc")
        settings = Settings.from_env()
        assert settings.chunk_size == 1000  # Default used
        errors = settings.validate()
        assert any("Invalid integer for TRACEVAULT_CHUNK_SIZE" in e for e in errors)

    def test_malformed_int_top_k(self, monkeypatch):
        """Test malformed int for top_k uses default."""
        monkeypatch.setenv("TRACEVAULT_TOP_K", "xyz")
        settings = Settings.from_env()
        assert settings.top_k == 5  # Default used
        errors = settings.validate()
        assert any("Invalid integer for TRACEVAULT_TOP_K" in e for e in errors)

    def test_malformed_float_hybrid_alpha(self, monkeypatch):
        """Test malformed float for hybrid_alpha uses default."""
        monkeypatch.setenv("TRACEVAULT_HYBRID_ALPHA", "not-a-number")
        settings = Settings.from_env()
        assert settings.hybrid_alpha == 0.5  # Default used
        errors = settings.validate()
        assert any("Invalid float for TRACEVAULT_HYBRID_ALPHA" in e for e in errors)

    def test_malformed_float_min_confidence(self, monkeypatch):
        """Test malformed float for min_confidence_threshold uses default."""
        monkeypatch.setenv("TRACEVAULT_MIN_CONFIDENCE", "bad-value")
        settings = Settings.from_env()
        assert settings.min_confidence_threshold == 0.7  # Default used
        errors = settings.validate()
        assert any("Invalid float for TRACEVAULT_MIN_CONFIDENCE" in e for e in errors)

    def test_malformed_int_max_unsupported_claims(self, monkeypatch):
        """Test malformed int for max_unsupported_claims uses default."""
        monkeypatch.setenv("TRACEVAULT_MAX_UNSUPPORTED_CLAIMS", "invalid")
        settings = Settings.from_env()
        assert settings.max_unsupported_claims == 0  # Default used
        errors = settings.validate()
        assert any("Invalid integer for TRACEVAULT_MAX_UNSUPPORTED_CLAIMS" in e for e in errors)

    def test_multiple_malformed_env_vars(self, monkeypatch):
        """Test multiple malformed values are all captured."""
        monkeypatch.setenv("TRACEVAULT_CHUNK_SIZE", "bad")
        monkeypatch.setenv("TRACEVAULT_TOP_K", "worse")
        monkeypatch.setenv("TRACEVAULT_HYBRID_ALPHA", "worst")

        settings = Settings.from_env()
        errors = settings.validate()

        # All defaults should be used
        assert settings.chunk_size == 1000
        assert settings.top_k == 5
        assert settings.hybrid_alpha == 0.5

        # All parse errors should be reported
        assert len([e for e in errors if "Invalid" in e]) == 3


class TestValidationBounds:
    """Test validation of field bounds."""

    def test_min_confidence_below_zero(self):
        """Test min_confidence_threshold < 0 is invalid."""
        settings = Settings(min_confidence_threshold=-0.1)
        errors = settings.validate()
        assert any("min_confidence_threshold" in e for e in errors)

    def test_min_confidence_above_one(self):
        """Test min_confidence_threshold > 1 is invalid."""
        settings = Settings(min_confidence_threshold=1.5)
        errors = settings.validate()
        assert any("min_confidence_threshold" in e for e in errors)

    def test_min_confidence_valid_bounds(self):
        """Test min_confidence_threshold at boundaries is valid."""
        settings = Settings(min_confidence_threshold=0.0)
        assert settings.validate() == []

        settings = Settings(min_confidence_threshold=1.0)
        assert settings.validate() == []

    def test_max_unsupported_claims_negative(self):
        """Test max_unsupported_claims < 0 is invalid."""
        settings = Settings(max_unsupported_claims=-1)
        errors = settings.validate()
        assert any("max_unsupported_claims" in e for e in errors)

    def test_max_unsupported_claims_zero_valid(self):
        """Test max_unsupported_claims = 0 is valid (strict mode)."""
        settings = Settings(max_unsupported_claims=0)
        assert settings.validate() == []

    def test_max_unsupported_claims_positive_valid(self):
        """Test max_unsupported_claims > 0 is valid (lenient mode)."""
        settings = Settings(max_unsupported_claims=5)
        assert settings.validate() == []

    def test_top_k_zero_invalid(self):
        """Test top_k <= 0 is invalid."""
        settings = Settings(top_k=0)
        errors = settings.validate()
        assert any("top_k" in e for e in errors)

    def test_top_k_negative_invalid(self):
        """Test top_k < 0 is invalid."""
        settings = Settings(top_k=-1)
        errors = settings.validate()
        assert any("top_k" in e for e in errors)

    def test_chunk_overlap_negative(self):
        """Test chunk_overlap < 0 is invalid."""
        settings = Settings(chunk_overlap=-10)
        errors = settings.validate()
        assert any("chunk_overlap" in e for e in errors)

    def test_chunk_overlap_zero_valid(self):
        """Test chunk_overlap = 0 is valid."""
        settings = Settings(chunk_overlap=0)
        assert settings.validate() == []

    def test_invalid_model_provider(self):
        """Test invalid model_provider is caught."""
        settings = Settings(model_provider="invalid")
        errors = settings.validate()
        assert any("model_provider" in e for e in errors)

    def test_valid_model_providers(self):
        """Test all valid model providers."""
        for provider in ["local", "ollama", "openai"]:
            settings = Settings(model_provider=provider)
            assert settings.validate() == []
