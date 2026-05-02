"""Tests for local model-based refinement (Phase 3B).

Tests cover:
- Model success path
- Timeout fallback
- Invalid JSON fallback
- No-new-facts violation fallback
- Critical token preservation
- Default no-model behavior
- Fallback equals rule_based_refine
- raw_text hash integrity
"""

from tracevault.refinement.config import LocalModelRefinementConfig
from tracevault.refinement.guardrails import ModelOutputGuardrails
from tracevault.refinement.model_adapter import (
    ModelConnectionError,
    ModelParseError,
    ModelRefinementOutput,
    ModelTimeoutError,
)
from tracevault.refinement.pipeline import (
    ModelAdapterProvider,
    refine_text,
)
from tracevault.refinement.refiner import rule_based_refine


class FakeModelAdapter:
    """Fake adapter for testing."""

    def __init__(
        self,
        return_cleaned: str = "cleaned",
        raise_error: Exception | None = None,
        model_name: str = "fake-model",
    ):
        self.return_cleaned = return_cleaned
        self.raise_error = raise_error
        self.model_name = model_name
        self.call_count = 0

    @property
    def name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        return True

    def refine_text(self, raw_text: str, prompt_version: str = "v1.0") -> ModelRefinementOutput:
        self.call_count += 1
        if self.raise_error:
            raise self.raise_error
        return ModelRefinementOutput(
            cleaned_text=self.return_cleaned,
            raw_text=raw_text,
            model_name=self.model_name,
        )


class FakeAdapterProvider(ModelAdapterProvider):
    """Fake provider for dependency injection."""

    def __init__(self, adapter: FakeModelAdapter | None):
        self.adapter = adapter

    def get_adapter(self) -> FakeModelAdapter | None:
        return self.adapter


class TestModelRefinementSuccess:
    """Tests for successful model refinement."""

    def test_model_refinement_succeeds_when_enabled(self):
        """Model refinement works when enabled and guardrails pass."""
        # Use input where model output doesn't add new words or excessive compression
        raw = "messy text here"
        # Model just normalizes, same words
        cleaned = "messy text here"
        adapter = FakeModelAdapter(return_cleaned=cleaned)
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        result, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert result == cleaned
        assert meta.refinement_method == "model_based"
        assert meta.model_name == "fake-model"
        assert meta.model_refinement_attempted is True
        assert meta.model_refinement_accepted is True
        assert adapter.call_count == 1

    def test_model_name_in_metadata(self):
        """Model name is recorded in metadata."""
        # Use input where model output doesn't add new words
        raw = "test text"
        cleaned = "test text"  # Same words, just normalized
        adapter = FakeModelAdapter(return_cleaned=cleaned, model_name="llama3.2")
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert meta.model_name == "llama3.2"
        assert meta.attempted_model_name == "llama3.2"


class TestDefaultBehavior:
    """Tests that default behavior does not call model."""

    def test_default_no_config_uses_rule_based(self):
        """Without config, uses rule-based only."""
        cleaned, meta = refine_text("  test  ")

        assert meta.refinement_method == "rule_based"
        assert meta.model_name is None
        assert meta.model_refinement_attempted is False

    def test_config_disabled_uses_rule_based(self):
        """With config.enabled=False, uses rule-based."""
        config = LocalModelRefinementConfig(enabled=False)
        cleaned, meta = refine_text("  test  ", config=config)

        assert meta.refinement_method == "rule_based"
        assert meta.model_refinement_attempted is False

    def test_no_adapter_falls_back_to_rule_based(self):
        """When adapter returns None, uses rule-based with attempted=True."""
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(None)  # No adapter

        cleaned, meta = refine_text("  test  ", config=config, adapter_provider=provider)

        assert meta.refinement_method == "rule_based"
        assert meta.model_refinement_attempted is True
        assert meta.model_refinement_accepted is False
        assert meta.fallback_reason == "adapter_unavailable"


class TestTimeoutFallback:
    """Tests for timeout fallback behavior."""

    def test_timeout_falls_back_to_rule_based(self):
        """Model timeout triggers rule-based fallback."""
        adapter = FakeModelAdapter(
            return_cleaned="ignored",
            raise_error=ModelTimeoutError("timeout"),
        )
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        cleaned, meta = refine_text("  raw  ", config=config, adapter_provider=provider)

        # Should have fallen back
        assert meta.refinement_method == "rule_based"
        assert meta.model_refinement_attempted is True
        assert meta.model_refinement_accepted is False
        assert meta.fallback_reason == "model_error: ModelTimeoutError"
        # Output should match rule_based
        expected, _ = rule_based_refine("  raw  ")
        assert cleaned == expected

    def test_connection_error_falls_back(self):
        """Connection error triggers fallback."""
        adapter = FakeModelAdapter(
            raise_error=ModelConnectionError("no host"),
        )
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text("raw", config=config, adapter_provider=provider)

        assert meta.fallback_reason == "model_error: ModelConnectionError"
        assert "model_fallback" in str(meta.warnings)


class TestInvalidJSONFallback:
    """Tests for invalid JSON fallback."""

    def test_invalid_json_falls_back(self):
        """Model parse error triggers fallback."""
        adapter = FakeModelAdapter(
            raise_error=ModelParseError("bad json"),
        )
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        cleaned, meta = refine_text("raw text", config=config, adapter_provider=provider)

        assert meta.refinement_method == "rule_based"
        assert meta.fallback_reason == "model_error: ModelParseError"

    def test_fallback_output_equals_rule_based(self):
        """Fallback output exactly equals rule_based_refine output."""
        raw = "  Version 2.3.1   released 2024-01-15  "
        adapter = FakeModelAdapter(raise_error=ModelTimeoutError())
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        cleaned, _ = refine_text(raw, config=config, adapter_provider=provider)
        expected, _ = rule_based_refine(raw)

        assert cleaned == expected


class TestGuardrailViolations:
    """Tests for guardrail violation fallback."""

    def test_added_numbers_triggers_fallback(self):
        """Model adding numbers triggers guardrail rejection."""
        # Model adds number not in raw
        adapter = FakeModelAdapter(return_cleaned="Version 999 released")
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        cleaned, meta = refine_text("Version released", config=config, adapter_provider=provider)

        # Should have fallen back due to added number
        assert meta.model_refinement_attempted is True
        assert meta.model_refinement_accepted is False
        assert "guardrail_violation" in meta.fallback_reason
        assert "added_numbers" in meta.guardrail_violations[0]
        # Output should be rule-based
        expected, _ = rule_based_refine("Version released")
        assert cleaned == expected

    def test_added_words_triggers_fallback(self):
        """Model adding significant words triggers rejection."""
        adapter = FakeModelAdapter(return_cleaned="The server crashed due to memory issues")
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text("Server crashed", config=config, adapter_provider=provider)

        assert meta.model_refinement_accepted is False
        assert any("added_words" in v for v in meta.guardrail_violations)

    def test_excessive_expansion_triggers_fallback(self):
        """Model expanding too much triggers rejection."""
        raw = "Short"
        # Expand by >20%
        expanded = "Short " + "x" * 100
        adapter = FakeModelAdapter(return_cleaned=expanded)
        config = LocalModelRefinementConfig(enabled=True, max_expansion_percent=20)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert meta.model_refinement_accepted is False
        assert any("excessive_expansion" in v for v in meta.guardrail_violations)

    def test_critical_token_loss_triggers_fallback(self):
        """Model losing critical tokens triggers rejection."""
        raw = "Version 2.3.1 at 03:42 UTC"
        cleaned = "Version at UTC"  # Lost numbers
        adapter = FakeModelAdapter(return_cleaned=cleaned)
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert meta.model_refinement_accepted is False
        assert any("critical_token_loss" in v for v in meta.guardrail_violations)


class TestRawTextIntegrity:
    """Tests for raw_text preservation."""

    def test_raw_text_hash_integrity_preserved(self):
        """raw_text hash is always computed from original."""
        raw = "Original text"
        adapter = FakeModelAdapter(return_cleaned="Cleaned")
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        # Hash should be of raw_text
        import hashlib
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert meta.source_raw_hash == expected_hash

    def test_raw_text_unchanged_in_fallback(self):
        """Fallback preserves raw_text exactly."""
        raw = "  Original   with   spaces  "
        adapter = FakeModelAdapter(raise_error=ModelTimeoutError())
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        cleaned, _ = refine_text(raw, config=config, adapter_provider=provider)

        # Fallback should apply rule-based, not return raw
        # But raw_text itself is never mutated in the pipeline
        assert cleaned != raw  # Rule-based normalizes
        assert "   " not in cleaned  # No triple spaces


class TestCriticalTokenPreservation:
    """Tests for critical token preservation guardrails."""

    def test_numbers_preserved_in_success(self):
        """Model preserving numbers passes guardrails."""
        raw = "Version 2.3.1 at 03:42"
        cleaned = "Version 2.3.1 at 03:42"  # Same numbers
        adapter = FakeModelAdapter(return_cleaned=cleaned)
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert meta.model_refinement_accepted is True
        assert not meta.guardrail_violations

    def test_dates_preserved(self):
        """Model preserving dates passes."""
        raw = "Event on 2024-01-15"
        cleaned = "Event on 2024-01-15"
        adapter = FakeModelAdapter(return_cleaned=cleaned)
        config = LocalModelRefinementConfig(enabled=True)
        provider = FakeAdapterProvider(adapter)

        _, meta = refine_text(raw, config=config, adapter_provider=provider)

        assert meta.model_refinement_accepted is True


class TestGuardrailsDirect:
    """Direct tests of ModelOutputGuardrails."""

    def test_guardrails_pass_clean_text(self):
        """Valid cleaned text passes all guardrails."""
        guardrails = ModelOutputGuardrails(max_compression_percent=100)  # Allow any compression
        result = guardrails.validate("  raw  ", "raw")

        assert result.passed is True
        assert result.cleaned_text == "raw"

    def test_guardrails_reject_empty_cleaned(self):
        """Empty cleaned from non-empty raw fails."""
        guardrails = ModelOutputGuardrails()
        result = guardrails.validate("text", "")

        assert result.passed is False
        assert "empty_cleaned_from_nonempty_raw" in result.violations

    def test_guardrails_reject_added_numbers(self):
        """Added numbers trigger violation."""
        guardrails = ModelOutputGuardrails()
        result = guardrails.validate("Version old", "Version 999")

        assert result.passed is False
        assert any("added_numbers" in v for v in result.violations)

    def test_guardrails_reject_excessive_expansion(self):
        """Expansion > threshold fails."""
        guardrails = ModelOutputGuardrails(max_expansion_percent=10)
        raw = "Short"
        cleaned = "Short " + "x" * 50  # >10% expansion

        result = guardrails.validate(raw, cleaned)

        assert result.passed is False
        assert any("excessive_expansion" in v for v in result.violations)

    def test_guardrails_reject_excessive_compression(self):
        """Compression > threshold fails."""
        guardrails = ModelOutputGuardrails(max_compression_percent=10)
        raw = "This is a longer text"
        cleaned = "Short"  # >10% compression

        result = guardrails.validate(raw, cleaned)

        assert result.passed is False
        assert any("excessive_compression" in v for v in result.violations)


class TestRefineDocumentMetadata:
    """Tests for refine_document metadata tracking (Phase 3B)."""

    def test_refine_document_default_does_not_accept_model(self):
        """Without config, refine_document uses rule-based only."""
        from tracevault.refinement.pipeline import refine_document

        result = refine_document("doc_001", "Hello world")

        assert result.metadata.refinement_method == "rule_based"
        assert result.metadata.model_refinement_attempted is False
        assert result.metadata.model_refinement_accepted is False
        assert result.metadata.model_name is None

    def test_refine_document_all_chunks_model_accepted(self):
        """When all chunks accept model output, document is model_based."""
        from tracevault.refinement.pipeline import refine_document

        # Create adapter that returns safe output (same words, just normalized)
        def safe_refine(raw_text: str, prompt_version: str = "v1.0") -> ModelRefinementOutput:
            # Return text with same words, just trimmed
            return ModelRefinementOutput(
                cleaned_text=raw_text.strip(),
                raw_text=raw_text,
                model_name="test-model",
            )

        class SafeAdapter:
            model_name = "test-model"
            call_count = 0

            def is_available(self) -> bool:
                return True

            def refine_text(self, raw_text: str, prompt_version: str = "v1.0") -> ModelRefinementOutput:
                self.call_count += 1
                return safe_refine(raw_text, prompt_version)

        adapter = SafeAdapter()
        config = LocalModelRefinementConfig(enabled=True, model_name="test-model")

        class Provider(ModelAdapterProvider):
            def get_adapter(self):
                return adapter

        # Use text that will create multiple chunks with chunk_size=10
        raw = "A B C D E F G H I J K L M N O P Q R S T"
        result = refine_document(
            "doc_001", raw, chunk_size=10, overlap=0,
            config=config, adapter_provider=Provider()
        )

        # All chunks should have been processed by model
        assert result.metadata.refinement_method == "model_based"
        assert result.metadata.model_refinement_attempted is True
        assert result.metadata.model_refinement_accepted is True
        assert result.metadata.attempted_model_name == "test-model"
        assert result.metadata.model_name == "test-model"
        assert adapter.call_count == result.total_chunks

    def test_refine_document_partial_fallback_preserves_audit_metadata(self):
        """When some chunks fail, document is rule_based with audit trail."""
        from tracevault.refinement.pipeline import refine_document

        class FlakyAdapter:
            """Adapter that succeeds on first chunk, fails on second."""
            model_name = "flaky-model"
            call_count = 0

            def is_available(self) -> bool:
                return True

            def refine_text(self, raw_text: str, prompt_version: str = "v1.0") -> ModelRefinementOutput:
                self.call_count += 1
                if self.call_count == 1:
                    # First chunk: safe output
                    return ModelRefinementOutput(
                        cleaned_text=raw_text.strip(),
                        raw_text=raw_text,
                        model_name=self.model_name,
                    )
                else:
                    # Second chunk: adds number (guardrail violation)
                    return ModelRefinementOutput(
                        cleaned_text=raw_text.strip() + " 999",
                        raw_text=raw_text,
                        model_name=self.model_name,
                    )

        adapter = FlakyAdapter()
        config = LocalModelRefinementConfig(enabled=True, model_name="flaky-model")

        class Provider(ModelAdapterProvider):
            def get_adapter(self):
                return adapter

        # Text that creates at least 2 chunks
        raw = "First chunk text here. Second chunk text here."
        result = refine_document(
            "doc_001", raw, chunk_size=20, overlap=0,
            config=config, adapter_provider=Provider()
        )

        # Should have fallen back to rule_based due to guardrail violation
        assert result.metadata.refinement_method == "rule_based"
        assert result.metadata.model_refinement_attempted is True
        assert result.metadata.model_refinement_accepted is False
        assert result.metadata.attempted_model_name == "flaky-model"
        assert result.metadata.fallback_reason is not None
        assert "partial_fallback" in result.metadata.fallback_reason
        # Should have warnings about guardrail violations
        assert any("guardrail" in str(w).lower() for w in result.metadata.warnings)

    def test_refine_document_adapter_unavailable_metadata(self):
        """When adapter returns None, metadata shows adapter_unavailable with attempted=True."""
        from tracevault.refinement.pipeline import refine_document

        config = LocalModelRefinementConfig(enabled=True, model_name="configured-model")

        class EmptyProvider(ModelAdapterProvider):
            def get_adapter(self):
                return None

        result = refine_document(
            "doc_001", "Test text",
            config=config, adapter_provider=EmptyProvider()
        )

        assert result.metadata.refinement_method == "rule_based"
        assert result.metadata.fallback_reason == "adapter_unavailable"
        assert result.metadata.attempted_model_name == "configured-model"
        assert result.metadata.model_refinement_attempted is True
        assert result.metadata.model_refinement_accepted is False
