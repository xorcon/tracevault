"""Semantic refinement package.

Provides deterministic chunking, rule-based refinement, and dual-context storage
for enterprise knowledge processing.

Architecture:
- Chunking: Splits raw_text into stable, traceable units
- Refinement: Cleans text without adding facts (rule-based for Phase 3A)
- Models: TextChunk, RefinementMetadata, RefinementResult
- Pipeline: Orchestration of chunking + refinement

Key principles:
- raw_text is the source of truth (never overwritten)
- cleaned_text is a retrieval aid only
- All operations are deterministic
- No external model calls in Phase 3A
"""

from tracevault.refinement.chunker import chunk_text
from tracevault.refinement.models import (
    RefinementMetadata,
    RefinementResult,
    TextChunk,
)
from tracevault.refinement.pipeline import refine_document, refine_text
from tracevault.refinement.refiner import (
    check_no_new_facts,
    rule_based_refine,
)

__all__ = [
    "chunk_text",
    "TextChunk",
    "RefinementMetadata",
    "RefinementResult",
    "rule_based_refine",
    "check_no_new_facts",
    "refine_document",
    "refine_text",
]
