"""TraceVault configuration settings.

This module provides configuration management for TraceVault with support for:
- Environment variable configuration
- Safe defaults for local-first operation
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

    # Validation
    min_confidence_threshold: float = 0.7
    max_unsupported_claims: int = 0

    @classmethod
    def from_env(cls) -> "Settings":
        """Create Settings from environment variables.

        Returns:
            Settings instance populated from environment or defaults.
        """
        return cls(
            data_dir=Path(os.getenv("TRACEVAULT_DATA_DIR", "./data")),
            log_level=os.getenv("TRACEVAULT_LOG_LEVEL", "INFO").upper(),
            model_provider=os.getenv("TRACEVAULT_MODEL_PROVIDER", "local").lower(),
            embedding_model=os.getenv("TRACEVAULT_EMBEDDING_MODEL"),
            reasoning_model=os.getenv("TRACEVAULT_REASONING_MODEL"),
            chunk_size=int(os.getenv("TRACEVAULT_CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("TRACEVAULT_CHUNK_OVERLAP", "200")),
            top_k=int(os.getenv("TRACEVAULT_TOP_K", "5")),
            hybrid_alpha=float(os.getenv("TRACEVAULT_HYBRID_ALPHA", "0.5")),
            min_confidence_threshold=float(
                os.getenv("TRACEVAULT_MIN_CONFIDENCE", "0.7")
            ),
            max_unsupported_claims=int(
                os.getenv("TRACEVAULT_MAX_UNSUPPORTED_CLAIMS", "0")
            ),
        )

    def validate(self) -> list[str]:
        """Validate settings.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if self.log_level not in valid_levels:
            errors.append(f"Invalid log_level: {self.log_level}")

        if not 0 <= self.hybrid_alpha <= 1:
            errors.append(f"hybrid_alpha must be between 0 and 1: {self.hybrid_alpha}")

        if self.chunk_size <= 0:
            errors.append(f"chunk_size must be positive: {self.chunk_size}")

        if self.chunk_overlap >= self.chunk_size:
            errors.append(f"chunk_overlap must be less than chunk_size")

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
