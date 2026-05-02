"""Unit tests for RefinementPromptBuilder.

Tests cover prompt construction, version traceability, and
the no-new-facts guardrail properties of the generated prompts.
"""

from tracevault.refinement.prompt_builder import (
    RefinementPrompt,
    RefinementPromptBuilder,
)


class TestRefinementPromptBuilderBasic:
    """Basic prompt construction tests."""

    def test_build_returns_refinement_prompt(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("hello world")

        assert isinstance(result, RefinementPrompt)
        assert result.input_text == "hello world"

    def test_full_prompt_contains_input_text(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("sample text")

        assert "sample text" in result.full_prompt

    def test_full_prompt_contains_system_and_user(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("sample text")

        assert result.system_instruction in result.full_prompt
        assert result.user_instruction in result.full_prompt

    def test_exclude_system_prompt(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("sample text", include_system_prompt=False)

        assert result.system_instruction not in result.full_prompt
        assert result.user_instruction == result.full_prompt

    def test_get_full_prompt_convenience(self):
        builder = RefinementPromptBuilder(version="v1.0")
        full = builder.get_full_prompt("sample text")

        assert isinstance(full, str)
        assert "sample text" in full


class TestRefinementPromptVersionTraceability:
    """Version traceability — the core fix for Phase 3B."""

    def test_version_appears_in_full_prompt(self):
        builder = RefinementPromptBuilder(version="v1")
        result = builder.build("test")

        assert "v1" in result.full_prompt

    def test_different_version_appears_in_full_prompt(self):
        builder = RefinementPromptBuilder(version="v2")
        result = builder.build("test")

        assert "v2" in result.full_prompt

    def test_different_versions_produce_different_prompts(self):
        builder_v1 = RefinementPromptBuilder(version="v1")
        builder_v2 = RefinementPromptBuilder(version="v2")

        prompt_v1 = builder_v1.build("test text")
        prompt_v2 = builder_v2.build("test text")

        assert prompt_v1.full_prompt != prompt_v2.full_prompt

    def test_version_in_user_instruction(self):
        builder = RefinementPromptBuilder(version="v3.0")
        result = builder.build("test")

        assert "v3.0" in result.user_instruction

    def test_version_not_in_system_instruction(self):
        """Version lives in user instruction, not system instruction."""
        builder_v1 = RefinementPromptBuilder(version="v1")
        builder_v2 = RefinementPromptBuilder(version="v2")

        sys_v1 = builder_v1._get_system_instruction()
        sys_v2 = builder_v2._get_system_instruction()

        assert sys_v1 == sys_v2

    def test_default_version_is_v1_0(self):
        builder = RefinementPromptBuilder()

        assert builder.version == "v1.0"


class TestRefinementPromptContent:
    """Prompt content contains expected guardrail instructions."""

    def test_system_instruction_enforces_fact_preservation(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("test")

        assert "Preserve ALL facts" in result.system_instruction

    def test_system_instruction_requires_json_output(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("test")

        assert "JSON" in result.system_instruction

    def test_user_instruction_contains_json_format(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("test")

        assert "cleaned_text" in result.user_instruction

    def test_prompt_version_label_in_user_instruction(self):
        builder = RefinementPromptBuilder(version="v1.0")
        result = builder.build("test")

        assert "Prompt version:" in result.user_instruction
