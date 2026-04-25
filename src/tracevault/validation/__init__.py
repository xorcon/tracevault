"""Validation module.

Implements verification layer:
- Citation support checking
- Unsupported claim detection
- Confidence scoring
- Raw vs cleaned conflict detection

Phase 5 will implement the verification pipeline.
"""

from typing import Protocol, runtime_checkable, TypedDict


class ValidationResult(TypedDict):
    """Result from validation."""
    is_valid: bool
    citation_coverage: float  # 0.0 to 1.0
    unsupported_claims: list[str]
    conflicts: list[str]
    confidence_score: float
    issues: list[str]


@runtime_checkable
class Validator(Protocol):
    """Protocol for answer validation."""

    def validate(
        self,
        answer: str,
        evidence_citations: list[str],
        evidence_pack: dict
    ) -> ValidationResult:
        """Validate answer against evidence.

        Args:
            answer: Generated answer.
            evidence_citations: Cited chunk IDs.
            evidence_pack: Original evidence used.

        Returns:
            Validation result with coverage and issues.
        """
        ...
