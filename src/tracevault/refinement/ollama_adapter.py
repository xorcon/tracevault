"""Ollama local model adapter implementation.

Provides connection to Ollama server for semantic refinement with
comprehensive error handling and JSON output parsing.
"""

import json

import requests

from tracevault.refinement.model_adapter import (
    ModelConnectionError,
    ModelParseError,
    ModelRefinementOutput,
    ModelTimeoutError,
)
from tracevault.refinement.prompt_builder import RefinementPromptBuilder


class OllamaModelAdapter:
    """Adapter for Ollama local model server.

    Communicates with Ollama API at http://localhost:11434 (default)
    to perform semantic refinement with JSON output.

    Args:
        host: Ollama API host URL
        model_name: Model to use (e.g., "llama3.2", "gemma:2b")
        timeout_seconds: Request timeout
        max_tokens: Maximum generation tokens
        temperature: Sampling temperature

    Example:
        >>> adapter = OllamaModelAdapter(model_name="llama3.2")
        >>> if adapter.is_available():
        ...     output = adapter.refine_text("  messy   text  ")
        ...     print(output.cleaned_text)
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        timeout_seconds: int = 30,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        self.host = host.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        # Prompt builder is the single source of truth for prompts
        self.prompt_builder = RefinementPromptBuilder()

    @property
    def name(self) -> str:
        """Return adapter identifier."""
        return f"ollama:{self.model_name}"

    def is_available(self) -> bool:
        """Check if Ollama server and model are available.

        Returns:
            True if server responds and model exists
        """
        try:
            # Check if server is running
            resp = requests.get(
                f"{self.host}/api/tags",
                timeout=5,
            )
            if resp.status_code != 200:
                return False

            # Check if model exists
            data = resp.json()
            model_names = [m["name"].split(":")[0] for m in data.get("models", [])]
            return self.model_name.split(":")[0] in model_names

        except (requests.RequestException, json.JSONDecodeError):
            return False

    def refine_text(
        self,
        raw_text: str,
        prompt_version: str = "v1.0",
    ) -> ModelRefinementOutput:
        """Refine text using Ollama model.

        Args:
            raw_text: Original text to refine
            prompt_version: Version identifier passed to RefinementPromptBuilder

        Returns:
            ModelRefinementOutput with cleaned_text

        Raises:
            ModelTimeoutError: If request exceeds timeout_seconds
            ModelConnectionError: If Ollama server unreachable
            ModelParseError: If model output is not valid JSON
        """
        if not raw_text:
            return ModelRefinementOutput(
                cleaned_text="",
                raw_text="",
                model_name=self.model_name,
            )

        # Build refinement prompt using RefinementPromptBuilder
        # prompt_version is passed to configure the builder
        builder = RefinementPromptBuilder(version=prompt_version)
        prompt_obj = builder.build(raw_text)
        prompt = prompt_obj.full_prompt

        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "format": "json",  # Request JSON output
                },
                timeout=self.timeout_seconds,
            )

            if resp.status_code != 200:
                raise ModelConnectionError(
                    f"Ollama API error: {resp.status_code} {resp.text}"
                )

            result = resp.json()
            model_output = result.get("response", "")

            # Parse JSON output
            cleaned_text = self._extract_cleaned_text(model_output)

            # Extract token usage if available
            token_usage = None
            if "eval_count" in result:
                token_usage = {
                    "input_tokens": result.get("prompt_eval_count", 0),
                    "output_tokens": result.get("eval_count", 0),
                }

            return ModelRefinementOutput(
                cleaned_text=cleaned_text,
                raw_text=raw_text,
                model_name=self.model_name,
                token_usage=token_usage,
            )

        except requests.Timeout as e:
            raise ModelTimeoutError(
                f"Model request timed out after {self.timeout_seconds}s"
            ) from e
        except requests.ConnectionError as e:
            raise ModelConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Is Ollama running? Try: ollama serve"
            ) from e
        except requests.RequestException as e:
            raise ModelConnectionError(f"Ollama request failed: {e}") from e

    def _extract_cleaned_text(self, json_output: str) -> str:
        """Extract cleaned_text from model JSON output.

        Args:
            json_output: Raw JSON string from model

        Returns:
            Extracted cleaned_text value

        Raises:
            ModelParseError: If JSON invalid or cleaned_text missing
        """
        # Clean up potential markdown code blocks
        json_str = json_output.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                raise ModelParseError("Model output is not a JSON object")

            if "cleaned_text" not in data:
                raise ModelParseError(
                    "Model output missing 'cleaned_text' field. "
                    f"Got keys: {list(data.keys())}"
                )

            cleaned = data["cleaned_text"]
            if not isinstance(cleaned, str):
                raise ModelParseError(
                    f"cleaned_text is not a string, got {type(cleaned)}"
                )

            return cleaned

        except json.JSONDecodeError as e:
            raise ModelParseError(f"Invalid JSON from model: {e}\nOutput: {json_output[:200]}") from e
