"""Prompt builder for model-based semantic refinement.

Constructs prompts that guide local models to produce safe, traceable
refinement output while preserving facts and producing valid JSON.
"""

from dataclasses import dataclass


@dataclass
class RefinementPrompt:
    """Structured refinement prompt.

    Attributes:
        system_instruction: System-level guidance
        user_instruction: Task-specific instructions
        input_text: Text to be refined
        full_prompt: Complete concatenated prompt
    """

    system_instruction: str
    user_instruction: str
    input_text: str
    full_prompt: str


class RefinementPromptBuilder:
    """Builds prompts for semantic refinement.

    Creates prompts that enforce:
    - Fact preservation (no additions/deletions)
    - JSON output format for parsing
    - Minimal whitespace normalization only
    - Traceability to raw_text

    Args:
        version: Prompt version identifier (e.g., "v1.0")
    """

    def __init__(self, version: str = "v1.0"):
        self.version = version

    def build(
        self,
        raw_text: str,
        include_system_prompt: bool = True,
    ) -> RefinementPrompt:
        """Build refinement prompt.

        Args:
            raw_text: Original text to refine
            include_system_prompt: Whether to include system instruction

        Returns:
            RefinementPrompt with all components
        """
        system = self._get_system_instruction()
        user = self._get_user_instruction(raw_text)

        if include_system_prompt:
            full = f"{system}\n\n{user}"
        else:
            full = user

        return RefinementPrompt(
            system_instruction=system,
            user_instruction=user,
            input_text=raw_text,
            full_prompt=full,
        )

    def _get_system_instruction(self) -> str:
        """Get system-level instruction.

        Returns:
            System prompt enforcing fact preservation and JSON output
        """
        return """You are a text normalization assistant for an enterprise knowledge system.
Your task is to clean whitespace and formatting while preserving ALL content.

CRITICAL RULES:
1. Preserve ALL facts, numbers, names, dates, IDs, technical terms exactly
2. Never add, remove, summarize, or translate content
3. Only normalize: trim edges, reduce excessive blank lines (3+ to 2), reduce excessive spaces (3+ to 1-2)
4. Preserve indentation in code blocks and structured text
5. Output MUST be valid JSON with exactly one key: "cleaned_text"
6. If you cannot safely clean the text, return it unchanged in cleaned_text

This is for audit-critical enterprise data. Accuracy > aesthetics."""

    def _get_user_instruction(self, raw_text: str) -> str:
        """Get user-level instruction with input.

        Args:
            raw_text: Text to be refined

        Returns:
            User prompt with input text
        """
        return f"""Refine the following text by normalizing whitespace only.
Preserve all facts, numbers, and structure.

Input (preserve exactly, only normalize whitespace):
---
{raw_text}
---

Output ONLY valid JSON in this exact format:
{{
  "cleaned_text": "your cleaned text here"
}}

Do not add explanations, markdown, or extra text. Only JSON."""

    def get_full_prompt(self, raw_text: str) -> str:
        """Get complete prompt as single string.

        Args:
            raw_text: Text to refine

        Returns:
            Complete prompt string
        """
        prompt = self.build(raw_text)
        return prompt.full_prompt
