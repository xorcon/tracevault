"""TraceVault configuration settings.

This module provides configuration management for TraceVault with support for:
- Environment variable configuration
- Safe defaults for local-first operation
- Graceful handling of malformed environment variables
- No external dependencies

Environment Variables:
    TRACEVAULT_DATA_DIR: Local data directory (default: ./data)
    TRACEVAULT_LOG_LEVEL: Logging level (default: INFO)
    TRACEVAULT_MODEL_PROVIDER: Model provider (default: local)
    TRACEVAULT_EMBEDDING_MODEL: Embedding model name
    TRACEVAULT_REASONING_MODEL: Reasoning model name
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    """TraceVault configuration settings.

    Attributes:
        data_dir: Local directory for storing documents and indexes.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        model_provider: Model provider type (local, ollama, openai).
        embedding_model: Name of the embedding model.
        reasoning_model: Name of the reasoning/generation model.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between chunks in characters.
        top_k: Number of results to retrieve.
        hybrid_alpha: Weight for hybrid retrieval (0=BM25 only, 1=vector only).
        min_confidence_threshold: Minimum confidence score for answers (0.0-1.0).
        max_unsupported_claims: Maximum allowed unsupported claims (>=0).
    """

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("./data"))

    # Logging
    log_level: str = "INFO"

    # Model configuration
    model_provider: str = "local"
    embedding_model: Optional[str] = None
    reasoning_model: Optional[str] = None

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval
    top_k: int = 5
    hybrid_alpha: float = 0.5

    # Validation (implements architecture verification layer)
    min_confidence_threshold: float = 0.7
    max_unsupported_claims: int = 0

    # Parse errors captured during from_env()
    _parse_errors: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        """Create Settings from environment variables.

        Malformed values are silently replaced with defaults and reported
        via validate(). No exceptions are raised.

        Returns:
            Settings instance populated from environment or defaults.
        """
        errors = []

        # Parse integers with safe defaults
        def safe_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except (ValueError, TypeError):
                errors.append(f"Invalid integer for {key}")
                return default

        # Parse floats with safe defaults
        def safe_float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except (ValueError, TypeError):
                errors.append(f"Invalid float for {key}")
                return default

        settings = cls(
            data_dir=Path(os.getenv("TRACEVAULT_DATA_DIR", "./data")),
            log_level=os.getenv("TRACEVAULT_LOG_LEVEL", "INFO").upper(),
            model_provider=os.getenv("TRACEVAULT_MODEL_PROVIDER", "local").lower(),
            embedding_model=os.getenv("TRACEVAULT_EMBEDDING_MODEL"),
            reasoning_model=os.getenv("TRACEVAULT_REASONING_MODEL"),
            chunk_size=safe_int("TRACEVAULT_CHUNK_SIZE", 1000),
            chunk_overlap=safe_int("TRACEVAULT_CHUNK_OVERLAP", 200),
            top_k=safe_int("TRACEVAULT_TOP_K", 5),
            hybrid_alpha=safe_float("TRACEVAULT_HYBRID_ALPHA", 0.5),
            min_confidence_threshold=safe_float("TRACEVAULT_MIN_CONFIDENCE", 0.7),
            max_unsupported_claims=safe_int("TRACEVAULT_MAX_UNSUPPORTED_CLAIMS", 0),
        )
        settings._parse_errors = errors
        return settings

    def validate(self) -> list[str]:
        """Validate settings.

        Returns:
            List of validation error messages (empty if valid). Includes
            parse errors from from_env() if any.
        """
        errors = list(self._parse_errors)  # Start with parse errors

        # Log level validation
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if self.log_level not in valid_levels:
            errors.append(f"Invalid log_level: {self.log_level}")

        # Model provider validation
        valid_providers = {"local", "ollama", "openai"}
        if self.model_provider not in valid_providers:
            errors.append(f"Invalid model_provider: {self.model_provider}")

        # Chunking validation
        if self.chunk_size <= 0:
            errors.append(f"chunk_size must be positive: {self.chunk_size}")

        if self.chunk_overlap < 0:
            errors.append(f"chunk_overlap must be non-negative: {self.chunk_overlap}")

        if self.chunk_overlap >= self.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")

        # Retrieval validation
        if self.top_k <= 0:
            errors.append(f"top_k must be positive: {self.top_k}")

        if not 0 <= self.hybrid_alpha <= 1:
            errors.append(f"hybrid_alpha must be between 0 and 1: {self.hybrid_alpha}")

        # Validation/verification layer bounds
        if not 0 <= self.min_confidence_threshold <= 1:
            errors.append(
                f"min_confidence_threshold must be between 0 and 1: "
                f"{self.min_confidence_threshold}"
            )

        if self.max_unsupported_claims < 0:
            errors.append(
                f"max_unsupported_claims must be non-negative: "
                f"{self.max_unsupported_claims}"
            )

        return errors


# Module-level singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the current settings instance.

    Returns:
        Settings instance, loaded from environment if not already loaded.
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment.

    Returns:
        Fresh Settings instance from current environment.
    """
    global _settings
    _settings = Settings.from_env()
    return _settings
