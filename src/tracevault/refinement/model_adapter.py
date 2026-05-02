"""Abstract protocol for local model adapters.

Defines the interface that all local model implementations must follow.
Enables dependency injection for testing and multiple backend support.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelRefinementOutput:
    """Output from model-based refinement.

    Attributes:
        cleaned_text: Refined text output from model
        raw_text: Original input (preserved for verification)
        model_name: Name of model that produced output
        token_usage: Dict with input/output token counts (optional)
    """

    cleaned_text: str
    raw_text: str
    model_name: str
    token_usage: dict | None = None


class ModelRefinementError(Exception):
    """Base exception for model refinement errors."""
    pass


class ModelTimeoutError(ModelRefinementError):
    """Raised when model request times out."""
    pass


class ModelConnectionError(ModelRefinementError):
    """Raised when model server is unreachable."""
    pass


class ModelParseError(ModelRefinementError):
    """Raised when model output cannot be parsed."""
    pass


class ModelAdapter(Protocol):
    """Protocol for local model refinement adapters.

    Implementations must provide:
    - refine_text: Main refinement method
    - is_available: Health check
    - model_name: Identifier
    """

    @property
    def model_name(self) -> str:
        """Return the model name."""
        ...

    def is_available(self) -> bool:
        """Check if model server is available.

        Returns:
            True if server is reachable and model is loaded
        """
        ...

    @abstractmethod
    def refine_text(
        self,
        raw_text: str,
        prompt_version: str = "v1.0",
    ) -> ModelRefinementOutput:
        """Refine text using local model.

        Args:
            raw_text: Original text to refine
            prompt_version: Version of refinement prompt

        Returns:
            ModelRefinementOutput with cleaned_text and metadata

        Raises:
            ModelTimeoutError: If request exceeds timeout
            ModelConnectionError: If server unreachable
            ModelParseError: If output cannot be parsed
        """
        ...
