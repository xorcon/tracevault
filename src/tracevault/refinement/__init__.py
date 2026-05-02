"""Semantic refinement package.

Provides deterministic chunking, rule-based refinement, and optional local
model-based refinement with dual-context storage for enterprise knowledge
processing.

Architecture:
- Chunking: Splits raw_text into stable, traceable units
- Refinement: Cleans text without adding facts (rule-based default, model optional)
- Models: TextChunk, RefinementMetadata, RefinementResult
- Pipeline: Orchestration of chunking + refinement with model fallback

Key principles:
- raw_text is the source of truth (never overwritten)
- cleaned_text is a retrieval aid only
- All operations are deterministic (model failures fallback to rule-based)
- Model refinement is opt-in only (Phase 3B)
"""

from tracevault.refinement.chunker import chunk_text
from tracevault.refinement.config import LocalModelRefinementConfig
from tracevault.refinement.guardrails import GuardrailResult, ModelOutputGuardrails
from tracevault.refinement.model_adapter import (
    ModelAdapter,
    ModelConnectionError,
    ModelParseError,
    ModelRefinementError,
    ModelRefinementOutput,
    ModelTimeoutError,
)
from tracevault.refinement.models import (
    RefinementMetadata,
    RefinementResult,
    TextChunk,
)
from tracevault.refinement.pipeline import (
    ModelAdapterProvider,
    refine_document,
    refine_text,
)
from tracevault.refinement.prompt_builder import (
    RefinementPrompt,
    RefinementPromptBuilder,
)
from tracevault.refinement.refiner import (
    check_no_new_facts,
    rule_based_refine,
)

__all__ = [
    # Core
    "chunk_text",
    "TextChunk",
    "RefinementMetadata",
    "RefinementResult",
    "rule_based_refine",
    "check_no_new_facts",
    "refine_document",
    "refine_text",
    # Phase 3B - Model refinement
    "LocalModelRefinementConfig",
    "ModelAdapter",
    "ModelRefinementError",
    "ModelTimeoutError",
    "ModelConnectionError",
    "ModelParseError",
    "ModelRefinementOutput",
    "ModelOutputGuardrails",
    "GuardrailResult",
    "ModelAdapterProvider",
    "RefinementPrompt",
    "RefinementPromptBuilder",
]
