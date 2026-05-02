"""Guardrails for model-based refinement output.

Validates model output against safety constraints before acceptance:
- JSON structure validation
- No-new-facts checks
- Critical token preservation
- Size expansion/compression limits
"""

import re
from dataclasses import dataclass, field

from tracevault.refinement.refiner import check_no_new_facts


@dataclass
class GuardrailResult:
    """Result of guardrail validation.

    Attributes:
        passed: Whether all guardrails passed
        violations: List of specific violations found
        cleaned_text: Validated cleaned text (None if failed)
        raw_text: Original raw text
    """

    passed: bool
    violations: list[str] = field(default_factory=list)
    cleaned_text: str | None = None
    raw_text: str = ""


class ModelOutputGuardrails:
    """Guardrails for validating model refinement output.

    Ensures model output is safe to use by checking:
    1. JSON structure (if applicable)
    2. No new facts added
    3. Critical tokens preserved (numbers, dates, IDs)
    4. Size within acceptable bounds
    5. Content not empty when raw is not empty

    Args:
        max_expansion_percent: Maximum allowed expansion (default: 20%)
        max_compression_percent: Maximum allowed compression (default: 30%)
        critical_token_loss_threshold: Max % critical tokens that can be lost (default: 0%)
    """

    def __init__(
        self,
        max_expansion_percent: float = 20.0,
        max_compression_percent: float = 30.0,
        critical_token_loss_threshold: float = 0.0,
    ):
        self.max_expansion_percent = max_expansion_percent
        self.max_compression_percent = max_compression_percent
        self.critical_token_loss_threshold = critical_token_loss_threshold

    def validate(
        self,
        raw_text: str,
        cleaned_text: str,
    ) -> GuardrailResult:
        """Validate cleaned text against guardrails.

        Args:
            raw_text: Original source text
            cleaned_text: Model output to validate

        Returns:
            GuardrailResult indicating pass/fail and violations
        """
        violations = []

        # Check 1: Empty cleaned from non-empty raw
        if raw_text and not cleaned_text:
            violations.append("empty_cleaned_from_nonempty_raw")
            return GuardrailResult(
                passed=False,
                violations=violations,
                raw_text=raw_text,
            )

        # Check 2: No new facts
        fact_warnings = check_no_new_facts(raw_text, cleaned_text)
        if fact_warnings.added_numbers:
            violations.append(f"added_numbers: {fact_warnings.added_numbers[:5]}")
        if fact_warnings.added_words:
            # Filter common normalization artifacts
            significant_words = [
                w for w in fact_warnings.added_words if len(w) > 3
            ]
            if significant_words:
                violations.append(f"added_words: {significant_words[:5]}")

        # Check 3: Critical token preservation
        critical_violation = self._check_critical_tokens(raw_text, cleaned_text)
        if critical_violation:
            violations.append(critical_violation)

        # Check 4: Size bounds
        size_violation = self._check_size_bounds(raw_text, cleaned_text)
        if size_violation:
            violations.append(size_violation)

        passed = len(violations) == 0

        return GuardrailResult(
            passed=passed,
            violations=violations,
            cleaned_text=cleaned_text if passed else None,
            raw_text=raw_text,
        )

    def _check_critical_tokens(self, raw_text: str, cleaned_text: str) -> str | None:
        """Check that critical tokens (numbers, dates, IDs) are preserved.

        Args:
            raw_text: Original text
            cleaned_text: Cleaned text

        Returns:
            Violation message if critical tokens lost, None if ok
        """
        # Extract critical tokens: numbers, dates, version strings, IDs
        raw_critical = self._extract_critical_tokens(raw_text)
        cleaned_critical = self._extract_critical_tokens(cleaned_text)

        if not raw_critical:
            return None

        # Check for lost tokens
        lost = raw_critical - cleaned_critical
        if lost:
            loss_percent = (len(lost) / len(raw_critical)) * 100
            if loss_percent > self.critical_token_loss_threshold:
                return f"critical_token_loss: {list(lost)[:5]} ({loss_percent:.1f}% loss)"

        return None

    def _extract_critical_tokens(self, text: str) -> set[str]:
        """Extract critical tokens that must be preserved.

        Args:
            text: Input text

        Returns:
            Set of critical tokens (numbers, dates, version strings, IDs)
        """
        tokens = set()

        # Numbers (including decimals)
        tokens.update(re.findall(r"\b\d+\.?\d*\b", text))

        # Dates (ISO format)
        tokens.update(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text))

        # Version strings (semver-like)
        tokens.update(re.findall(r"\b\d+\.\d+\.\d+\b", text))

        # Time stamps
        tokens.update(re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text))

        # UUIDs
        tokens.update(
            re.findall(
                r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
                text,
            )
        )

        # AWS-style region/zone IDs
        tokens.update(re.findall(r"\b[a-z]+-[a-z]+-\d+-[a-z]+\b", text))

        return tokens

    def _check_size_bounds(self, raw_text: str, cleaned_text: str) -> str | None:
        """Check that size change is within bounds.

        Args:
            raw_text: Original text
            cleaned_text: Cleaned text

        Returns:
            Violation message if out of bounds, None if ok
        """
        if not raw_text:
            return None

        raw_len = len(raw_text)
        cleaned_len = len(cleaned_text)

        # Check expansion
        if cleaned_len > raw_len:
            expansion = ((cleaned_len - raw_len) / raw_len) * 100
            if expansion > self.max_expansion_percent:
                return f"excessive_expansion: {expansion:.1f}% > {self.max_expansion_percent}%"

        # Check compression
        compression = ((raw_len - cleaned_len) / raw_len) * 100
        if compression > self.max_compression_percent:
            return f"excessive_compression: {compression:.1f}% > {self.max_compression_percent}%"

        return None

    def validate_json_structure(self, json_str: str) -> tuple[bool, str | None]:
        """Validate JSON structure has cleaned_text field.

        Args:
            json_str: JSON string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        import json

        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                return False, "Not a JSON object"
            if "cleaned_text" not in data:
                return False, "Missing 'cleaned_text' field"
            if not isinstance(data["cleaned_text"], str):
                return False, "cleaned_text is not a string"
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
