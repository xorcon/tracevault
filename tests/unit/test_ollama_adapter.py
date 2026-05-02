"""Unit tests for OllamaModelAdapter.

Tests cover error handling, JSON parsing, and prompt_version usage
using mocks only. No live Ollama server required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from tracevault.refinement.model_adapter import (
    ModelConnectionError,
    ModelParseError,
    ModelRefinementOutput,
    ModelTimeoutError,
)
from tracevault.refinement.ollama_adapter import OllamaModelAdapter


class TestOllamaAdapterTimeout:
    """Tests for timeout error handling."""

    def test_timeout_converted_to_model_timeout_error(self):
        """requests.Timeout is converted to ModelTimeoutError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
            timeout_seconds=5,
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_post.side_effect = requests.Timeout("Request timed out")

            with pytest.raises(ModelTimeoutError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "timed out" in str(exc_info.value).lower()
            assert "5s" in str(exc_info.value)


class TestOllamaAdapterConnection:
    """Tests for connection error handling."""

    def test_connection_error_converted_to_model_connection_error(self):
        """requests.ConnectionError is converted to ModelConnectionError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection refused")

            with pytest.raises(ModelConnectionError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "Cannot connect to Ollama" in str(exc_info.value)
            assert "localhost:11434" in str(exc_info.value)

    def test_non_200_response_raises_model_connection_error(self):
        """Non-200 HTTP response is converted to ModelConnectionError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            with pytest.raises(ModelConnectionError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "500" in str(exc_info.value)
            assert "Internal Server Error" in str(exc_info.value)

    def test_404_response_raises_model_connection_error(self):
        """404 response is converted to ModelConnectionError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Model not found"
            mock_post.return_value = mock_response

            with pytest.raises(ModelConnectionError):
                adapter.refine_text("test text", prompt_version="v1.0")


class TestOllamaAdapterJSONParsing:
    """Tests for JSON parsing and validation."""

    def test_malformed_json_raises_model_parse_error(self):
        """Malformed JSON response is converted to ModelParseError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "{ invalid json }"}
            mock_post.return_value = mock_response

            with pytest.raises(ModelParseError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "Invalid JSON" in str(exc_info.value)

    def test_fenced_json_parsed_successfully(self):
        """JSON wrapped in markdown code blocks is parsed successfully."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        fenced_json = "```json\n{\"cleaned_text\": \"cleaned result\"}\n```"

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": fenced_json}
            mock_post.return_value = mock_response

            result = adapter.refine_text("test text", prompt_version="v1.0")

            assert isinstance(result, ModelRefinementOutput)
            assert result.cleaned_text == "cleaned result"
            assert result.raw_text == "test text"

    def test_json_missing_cleaned_text_raises_model_parse_error(self):
        """JSON missing cleaned_text field is rejected with ModelParseError."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": json.dumps({"text": "wrong key"})}
            mock_post.return_value = mock_response

            with pytest.raises(ModelParseError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "cleaned_text" in str(exc_info.value)
            assert "missing" in str(exc_info.value).lower()

    def test_cleaned_text_not_string_raises_model_parse_error(self):
        """cleaned_text that is not a string is rejected."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": json.dumps({"cleaned_text": 12345})}
            mock_post.return_value = mock_response

            with pytest.raises(ModelParseError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "not a string" in str(exc_info.value)

    def test_json_array_raises_model_parse_error(self):
        """JSON array instead of object is rejected."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": json.dumps(["array", "not", "object"])}
            mock_post.return_value = mock_response

            with pytest.raises(ModelParseError) as exc_info:
                adapter.refine_text("test text", prompt_version="v1.0")

            assert "not a JSON object" in str(exc_info.value)


class TestOllamaAdapterPromptVersion:
    """Tests for prompt_version traceability."""

    def test_prompt_version_affects_prompt_sent(self):
        """prompt_version is included in or affects the actual prompt sent to requests.post."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": json.dumps({"cleaned_text": "cleaned"})
            }
            mock_post.return_value = mock_response

            # Call with specific prompt_version
            adapter.refine_text("test text", prompt_version="v2.0")

            # Verify requests.post was called
            assert mock_post.called
            call_args = mock_post.call_args

            # Check that prompt was included in the JSON payload
            json_payload = call_args.kwargs.get("json", {})
            assert "prompt" in json_payload
            assert "model" in json_payload
            assert json_payload["model"] == "llama3.2"

            # The prompt should contain the input text
            prompt = json_payload["prompt"]
            assert "test text" in prompt

            # CRITICAL: the prompt must contain the requested prompt_version
            assert "v2.0" in prompt
            assert "Prompt version:" in prompt

    def test_prompt_version_passed_to_builder(self):
        """prompt_version is passed to RefinementPromptBuilder."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.RefinementPromptBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_prompt_obj = MagicMock()
            mock_prompt_obj.full_prompt = "system\n\nuser\ntest text"
            mock_builder.build.return_value = mock_prompt_obj

            with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "response": json.dumps({"cleaned_text": "cleaned"})
                }
                mock_post.return_value = mock_response

                adapter.refine_text("test text", prompt_version="v3.0")

                # Verify builder was instantiated with the version
                mock_builder_class.assert_called_once_with(version="v3.0")
                # Verify build was called
                mock_builder.build.assert_called_once()

    def test_different_prompt_versions_produce_different_prompts(self):
        """Different prompt versions produce different prompt content."""
        from tracevault.refinement.prompt_builder import RefinementPromptBuilder

        builder_v1 = RefinementPromptBuilder(version="v1.0")
        builder_v2 = RefinementPromptBuilder(version="v2.0")

        assert builder_v1.version == "v1.0"
        assert builder_v2.version == "v2.0"

        # Both should build prompts successfully
        prompt_v1 = builder_v1.build("test")
        prompt_v2 = builder_v2.build("test")

        assert prompt_v1.input_text == "test"
        assert prompt_v2.input_text == "test"
        assert prompt_v1.full_prompt is not None
        assert prompt_v2.full_prompt is not None

        # CRITICAL: different versions must produce different prompt bodies
        assert prompt_v1.full_prompt != prompt_v2.full_prompt

        # Each prompt must contain its own version
        assert "v1.0" in prompt_v1.full_prompt
        assert "v2.0" in prompt_v2.full_prompt
        assert "v2.0" not in prompt_v1.full_prompt
        assert "v1.0" not in prompt_v2.full_prompt


class TestOllamaAdapterSuccess:
    """Tests for successful refinement."""

    def test_successful_refinement_returns_output(self):
        """Successful API call returns ModelRefinementOutput."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": json.dumps({"cleaned_text": "cleaned text"}),
                "eval_count": 10,
                "prompt_eval_count": 5,
            }
            mock_post.return_value = mock_response

            result = adapter.refine_text("  messy   text  ", prompt_version="v1.0")

            assert isinstance(result, ModelRefinementOutput)
            assert result.cleaned_text == "cleaned text"
            assert result.raw_text == "  messy   text  "
            assert result.model_name == "llama3.2"
            assert result.token_usage == {
                "input_tokens": 5,
                "output_tokens": 10,
            }

    def test_empty_input_returns_empty_output(self):
        """Empty input returns empty ModelRefinementOutput."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        result = adapter.refine_text("", prompt_version="v1.0")

        assert result.cleaned_text == ""
        assert result.raw_text == ""
        assert result.model_name == "llama3.2"

    def test_empty_string_input_returns_empty_output(self):
        """Whitespace-only input is processed."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": json.dumps({"cleaned_text": "cleaned"})
            }
            mock_post.return_value = mock_response

            result = adapter.refine_text("   ", prompt_version="v1.0")

            assert result.cleaned_text == "cleaned"
            assert result.raw_text == "   "


class TestOllamaAdapterIsAvailable:
    """Tests for is_available method."""

    def test_is_available_returns_true_when_server_and_model_exist(self):
        """is_available returns True when server responds and model exists."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama3.2:latest"},
                    {"name": "gemma:2b"},
                ]
            }
            mock_get.return_value = mock_response

            assert adapter.is_available() is True

    def test_is_available_returns_false_when_server_unreachable(self):
        """is_available returns False when server is unreachable."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError()

            assert adapter.is_available() is False

    def test_is_available_returns_false_when_model_not_found(self):
        """is_available returns False when model is not in list."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="nonexistent",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama3.2:latest"},
                ]
            }
            mock_get.return_value = mock_response

            assert adapter.is_available() is False

    def test_is_available_returns_false_on_non_200(self):
        """is_available returns False on non-200 response."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="llama3.2",
        )

        with patch("tracevault.refinement.ollama_adapter.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            assert adapter.is_available() is False


class TestOllamaAdapterName:
    """Tests for adapter name property."""

    def test_name_returns_ollama_prefix_with_model(self):
        """name property returns 'ollama:model_name'."""
        adapter = OllamaModelAdapter(
            host="http://localhost:11434",
            model_name="gemma:2b",
        )

        assert adapter.name == "ollama:gemma:2b"
