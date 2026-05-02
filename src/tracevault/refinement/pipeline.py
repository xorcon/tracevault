"""Refinement pipeline.

Orchestrates chunking and refinement to process documents into dual-context
chunks with raw_text preserved as source of truth.

Phase 3B adds optional local model refinement with deterministic fallback
to rule-based refinement when models are unavailable or fail guardrails.
"""

from typing import Protocol

from tracevault.refinement.chunker import chunk_text
from tracevault.refinement.config import LocalModelRefinementConfig
from tracevault.refinement.guardrails import ModelOutputGuardrails
from tracevault.refinement.model_adapter import (
    ModelAdapter,
    ModelRefinementError,
    ModelRefinementOutput,
)
from tracevault.refinement.models import (
    RefinementMetadata,
    RefinementResult,
    TextChunk,
)
from tracevault.refinement.refiner import rule_based_refine


class ModelAdapterProvider(Protocol):
    """Protocol for providing model adapters.

    Allows dependency injection for testing.
    """

    def get_adapter(self) -> ModelAdapter | None:
        """Return model adapter if available, None otherwise."""
        ...


def _get_default_model_adapter(config: LocalModelRefinementConfig) -> ModelAdapter | None:
    """Get default model adapter based on config.

    Args:
        config: Model refinement configuration

    Returns:
        ModelAdapter if enabled and importable, None otherwise
    """
    if not config.enabled:
        return None

    try:
        from tracevault.refinement.ollama_adapter import OllamaModelAdapter

        return OllamaModelAdapter(
            host=config.host,
            model_name=config.model_name,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
    except ImportError:
        return None


def _try_model_refine(
    raw_text: str,
    prompt_version: str,
    config: LocalModelRefinementConfig,
    adapter_provider: ModelAdapterProvider | None = None,
) -> tuple[str, RefinementMetadata]:
    """Attempt model refinement with fallback to rule-based.

    Args:
        raw_text: Original text to refine
        prompt_version: Version identifier
        config: Model refinement configuration
        adapter_provider: Optional provider for dependency injection

    Returns:
        Tuple of (cleaned_text, RefinementMetadata)

    Flow:
        1. If config.enabled=False, use rule_based immediately
        2. Get model adapter
        3. If adapter unavailable but config.enabled=True: rule-based with attempted_model_name
        4. Try model refinement
        5. Validate with guardrails
        6. If any failure, fallback to rule_based with metadata
    """
    # Check if model refinement is enabled
    if not config.enabled:
        return rule_based_refine(raw_text, prompt_version)

    # Get adapter
    if adapter_provider:
        adapter = adapter_provider.get_adapter()
    else:
        adapter = _get_default_model_adapter(config)

    # Record which model was attempted (for metadata)
    attempted_model = adapter.model_name if adapter else config.model_name

    if adapter is None:
        # Adapter unavailable but config.enabled=True
        # Use rule-based but record that we attempted model refinement
        cleaned, meta = rule_based_refine(raw_text, prompt_version)
        meta.attempted_model_name = attempted_model
        meta.model_refinement_attempted = True
        meta.model_refinement_accepted = False
        meta.fallback_reason = "adapter_unavailable"
        return cleaned, meta

    # Setup guardrails
    guardrails = ModelOutputGuardrails(
        max_expansion_percent=config.max_expansion_percent,
        max_compression_percent=config.max_compression_percent,
        critical_token_loss_threshold=config.critical_token_loss_threshold,
    )

    try:
        # Try model refinement
        output: ModelRefinementOutput = adapter.refine_text(raw_text, prompt_version)
        model_cleaned = output.cleaned_text

        # Validate with guardrails
        guardrail_result = guardrails.validate(raw_text, model_cleaned)

        if not guardrail_result.passed:
            # Guardrails failed, fallback
            fallback_reason = f"guardrail_violation: {guardrail_result.violations[0]}"
            cleaned, meta = rule_based_refine(raw_text, prompt_version)

            # Update metadata to show model was attempted but rejected
            meta.model_refinement_attempted = True
            meta.model_refinement_accepted = False
            meta.attempted_model_name = adapter.model_name
            meta.guardrail_violations = guardrail_result.violations
            meta.fallback_reason = fallback_reason
            # model_name remains None since we fell back to rule-based

            return cleaned, meta

        # Success! Return model output with metadata
        metadata = RefinementMetadata(
            refinement_method="model_based",
            prompt_version=prompt_version,
            model_name=adapter.model_name,
            attempted_model_name=adapter.model_name,
            created_at=RefinementMetadata.get_current_timestamp(),
            no_new_facts_checked=True,
            source_raw_hash=TextChunk.compute_raw_hash(raw_text) if raw_text else None,
            cleaned_text_length=len(model_cleaned),
            raw_text_length=len(raw_text),
            model_refinement_attempted=True,
            model_refinement_accepted=True,
        )

        return model_cleaned, metadata

    except ModelRefinementError as e:
        # Model error, fallback to rule-based
        fallback_reason = f"model_error: {type(e).__name__}"
        cleaned, meta = rule_based_refine(raw_text, prompt_version)

        # Update metadata
        meta.model_refinement_attempted = True
        meta.model_refinement_accepted = False
        meta.attempted_model_name = adapter.model_name
        meta.fallback_reason = fallback_reason
        meta.warnings.append(f"model_fallback: {str(e)[:100]}")
        # model_name remains None since we fell back to rule-based

        return cleaned, meta


def refine_text(
    raw_text: str,
    prompt_version: str = "v1.0",
    config: LocalModelRefinementConfig | None = None,
    adapter_provider: ModelAdapterProvider | None = None,
) -> tuple[str, RefinementMetadata]:
    """Refine a single text segment.

    Args:
        raw_text: Original text to refine
        prompt_version: Version identifier for refinement rules
        config: Optional model refinement config (if None, uses rule-based only)
        adapter_provider: Optional adapter provider for dependency injection

    Returns:
        Tuple of (cleaned_text, RefinementMetadata)
    """
    if config is None:
        # No config = rule-based only (Phase 3A behavior)
        return rule_based_refine(raw_text, prompt_version)

    # Try model with fallback
    return _try_model_refine(
        raw_text, prompt_version, config, adapter_provider
    )


def refine_document(
    document_id: str,
    raw_text: str,
    chunk_size: int = 1000,
    overlap: int | None = None,
    prompt_version: str = "v1.0",
    config: LocalModelRefinementConfig | None = None,
    adapter_provider: ModelAdapterProvider | None = None,
) -> RefinementResult:
    """Refine a full document through chunking and refinement.

    This is the main entry point for Phase 3A/3B refinement:
    1. Splits raw_text into deterministic chunks
    2. Applies refinement (model-based if enabled, else rule-based)
    3. Preserves raw_text exactly in each chunk
    4. Stores cleaned_text separately
    5. Attaches refinement metadata

    Args:
        document_id: Document identifier
        raw_text: Original document text (preserved exactly)
        chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks (default: 200, or auto-computed if chunk_size <= 200)
        prompt_version: Version identifier for refinement rules
        config: Optional model refinement config (if None, uses rule-based only)
        adapter_provider: Optional adapter provider for dependency injection

    Returns:
        RefinementResult with chunks, metadata, and statistics

    Example:
        >>> result = refine_document("doc_001", "Hello world", chunk_size=5)
        >>> len(result.chunks)
        3
        >>> result.chunks[0].raw_text
        'Hello'
        >>> result.chunks[0].cleaned_text
        'Hello'
    """
    # Step 1: Chunk the raw text (preserves raw_text exactly)
    chunks = chunk_text(
        document_id=document_id,
        raw_text=raw_text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    # Step 2: Refine each chunk
    refined_chunks: list[TextChunk] = []
    all_warnings: list[str] = []
    model_attempts = 0
    model_accepts = 0
    model_fallbacks = 0

    for chunk in chunks:
        # Apply refinement (model or rule-based)
        cleaned_text, chunk_metadata = refine_text(
            chunk.raw_text,
            prompt_version=prompt_version,
            config=config,
            adapter_provider=adapter_provider,
        )

        # Track model statistics
        if chunk_metadata.model_refinement_attempted:
            model_attempts += 1
            if chunk_metadata.model_refinement_accepted:
                model_accepts += 1
            else:
                model_fallbacks += 1

        # Update chunk with cleaned text and full metadata
        refined_chunk = TextChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            raw_text=chunk.raw_text,  # Preserved exactly
            cleaned_text=cleaned_text,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            raw_text_hash=chunk.raw_text_hash,
            metadata={
                "refinement_method": chunk_metadata.refinement_method,
                "prompt_version": chunk_metadata.prompt_version,
                "model_name": chunk_metadata.model_name,
                "attempted_model_name": chunk_metadata.attempted_model_name,
                "created_at": chunk_metadata.created_at,
                "warnings": chunk_metadata.warnings,
                "no_new_facts_checked": chunk_metadata.no_new_facts_checked,
                "source_raw_hash": chunk_metadata.source_raw_hash,
                "raw_text_length": chunk_metadata.raw_text_length,
                "cleaned_text_length": chunk_metadata.cleaned_text_length,
                "model_refinement_attempted": chunk_metadata.model_refinement_attempted,
                "model_refinement_accepted": chunk_metadata.model_refinement_accepted,
                "guardrail_violations": chunk_metadata.guardrail_violations,
                "fallback_reason": chunk_metadata.fallback_reason,
            },
        )
        refined_chunks.append(refined_chunk)

        # Accumulate warnings for document-level metadata
        all_warnings.extend(chunk_metadata.warnings)

    # Compute actual cleaned text length (sum of all refined chunk cleaned_text)
    total_cleaned_chars = sum(len(c.cleaned_text) for c in refined_chunks)

    # Determine overall refinement method
    # Only "model_based" if ALL chunks that attempted model refinement accepted it
    if config and config.enabled:
        if model_attempts == 0:
            overall_method: str = "rule_based"
        elif model_fallbacks == 0:
            # All attempted chunks accepted model output
            overall_method = "model_based"
        else:
            # Partial fallback occurred
            overall_method = "rule_based"
    else:
        overall_method = "rule_based"

    # Determine overall model name (only set if overall_method is model_based)
    overall_model_name = None
    if overall_method == "model_based" and model_attempts > 0:
        for chunk in refined_chunks:
            if chunk.metadata.get("model_name"):
                overall_model_name = chunk.metadata["model_name"]
                break

    # Collect unique fallback reasons, guardrail violations, and attempted_model_name for document level
    all_fallback_reasons: set[str] = set()
    all_guardrail_violations: set[str] = set()
    attempted_model_names: set[str] = set()

    for chunk in refined_chunks:
        if chunk.metadata.get("fallback_reason"):
            all_fallback_reasons.add(chunk.metadata["fallback_reason"])
        for violation in chunk.metadata.get("guardrail_violations", []):
            all_guardrail_violations.add(violation)
        if chunk.metadata.get("attempted_model_name"):
            attempted_model_names.add(chunk.metadata["attempted_model_name"])

    # Determine attempted_model_name at document level
    # Priority: chunk metadata > config.model_name (if enabled)
    doc_attempted_model_name: str | None = None
    if attempted_model_names:
        # Use the first one found (should be consistent across chunks)
        doc_attempted_model_name = next(iter(attempted_model_names))
    elif config and config.enabled:
        doc_attempted_model_name = config.model_name

    # Step 3: Build overall metadata
    overall_metadata = RefinementMetadata(
        refinement_method=overall_method,
        prompt_version=prompt_version,
        model_name=overall_model_name,
        created_at=RefinementMetadata.get_current_timestamp(),
        warnings=list(set(all_warnings)),  # Deduplicate
        no_new_facts_checked=True,
        source_raw_hash=TextChunk.compute_raw_hash(raw_text) if raw_text else None,
        raw_text_length=len(raw_text),  # Document original length
        cleaned_text_length=total_cleaned_chars,  # Actual cleaned output length
        model_refinement_attempted=model_attempts > 0,
        model_refinement_accepted=(model_attempts > 0 and model_fallbacks == 0 and model_accepts == model_attempts),
        attempted_model_name=doc_attempted_model_name,
    )

    # Add fallback info if any chunks fell back or adapter was unavailable
    if all_fallback_reasons:
        # Check if any chunk had adapter_unavailable
        has_adapter_unavailable = any("adapter_unavailable" in r for r in all_fallback_reasons)
        if has_adapter_unavailable:
            overall_metadata.fallback_reason = "adapter_unavailable"
        else:
            overall_metadata.fallback_reason = f"partial_fallback: {model_fallbacks}/{model_attempts} chunks"

        # Add detailed fallback reasons as warnings
        for reason in all_fallback_reasons:
            if reason not in overall_metadata.warnings:
                overall_metadata.warnings.append(reason)
        # Add guardrail violations as warnings too
        for violation in all_guardrail_violations:
            if violation not in overall_metadata.warnings:
                overall_metadata.warnings.append(f"guardrail: {violation}")

    # Step 4: Return result with correct statistics
    return RefinementResult(
        document_id=document_id,
        chunks=refined_chunks,
        metadata=overall_metadata,
        total_chunks=len(refined_chunks),
        total_raw_chars=len(raw_text),  # Document length, not sum of chunks
        total_cleaned_chars=total_cleaned_chars,  # Actual cleaned output length
    )
