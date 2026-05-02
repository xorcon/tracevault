"""Configuration for local model-based semantic refinement.

Defines settings for optional local model refinement with deterministic
fallback to rule-based refinement when models are unavailable or fail.
"""

from dataclasses import dataclass


@dataclass
class LocalModelRefinementConfig:
    """Configuration for local model refinement.

    Attributes:
        enabled: Whether model refinement is enabled (default: False for safety)
        host: Local model server host (e.g., "http://localhost:11434" for Ollama)
        model_name: Model name to use (e.g., "llama3.2", "gemma:2b")
        timeout_seconds: Request timeout in seconds (default: 30)
        max_tokens: Maximum tokens to generate (default: 2048)
        temperature: Sampling temperature (default: 0.1 for deterministic output)

        # Guardrail thresholds
        max_expansion_percent: Maximum allowed expansion of cleaned vs raw (default: 20%)
        max_compression_percent: Maximum allowed compression (default: 30%)
        critical_token_loss_threshold: Maximum allowed loss of critical tokens (default: 0%)

    Note:
        Default enabled=False ensures Phase 3A behavior (rule-based only)
        unless explicitly configured otherwise.
    """

    enabled: bool = False
    host: str = "http://localhost:11434"
    model_name: str = "llama3.2"
    timeout_seconds: int = 30
    max_tokens: int = 2048
    temperature: float = 0.1

    # Guardrail thresholds
    max_expansion_percent: float = 20.0
    max_compression_percent: float = 30.0
    critical_token_loss_threshold: float = 0.0

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not 0 <= self.max_expansion_percent <= 100:
            raise ValueError("max_expansion_percent must be between 0 and 100")
        if not 0 <= self.max_compression_percent <= 100:
            raise ValueError("max_compression_percent must be between 0 and 100")
        if not 0 <= self.critical_token_loss_threshold <= 100:
            raise ValueError("critical_token_loss_threshold must be between 0 and 100")
