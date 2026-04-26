"""Reasoning module.

Implements grounded reasoning with evidence constraints.
Reasoning modes:
- synthesis: Combine multiple sources
- pattern_detection: Identify recurring patterns
- temporal_analysis: Analyze time-series knowledge
- scenario_planning: Evaluate hypothetical scenarios

Phase 5 will implement the reasoning engine.
"""

from typing import Protocol, TypedDict, runtime_checkable


class ReasoningResult(TypedDict):
    """Result from grounded reasoning."""
    answer: str
    evidence_citations: list[str]  # chunk_ids
    confidence: float
    unsupported_claims: list[str]
    reasoning_mode: str


@runtime_checkable
class ReasoningEngine(Protocol):
    """Protocol for grounded reasoning."""

    def reason(
        self,
        query: str,
        evidence_pack: dict,
        mode: str = "synthesis"
    ) -> ReasoningResult:
        """Generate grounded answer from evidence.

        Args:
            query: User question.
            evidence_pack: Retrieved evidence context.
            mode: Reasoning mode (synthesis, pattern_detection, etc.).

        Returns:
            Reasoning result with answer and traceability.
        """
        ...
