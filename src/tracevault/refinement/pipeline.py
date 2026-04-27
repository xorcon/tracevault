"""Refinement pipeline.

Orchestrates chunking and refinement to process documents into dual-context
chunks with raw_text preserved as source of truth.
"""

from tracevault.refinement.chunker import chunk_text
from tracevault.refinement.models import (
    RefinementMetadata,
    RefinementResult,
    TextChunk,
)
from tracevault.refinement.refiner import rule_based_refine


def refine_text(
    raw_text: str,
    prompt_version: str = "v1.0",
) -> tuple[str, RefinementMetadata]:
    """Refine a single text segment.

    Args:
        raw_text: Original text to refine
        prompt_version: Version identifier for refinement rules

    Returns:
        Tuple of (cleaned_text, RefinementMetadata)
    """
    return rule_based_refine(raw_text, prompt_version)


def refine_document(
    document_id: str,
    raw_text: str,
    chunk_size: int = 1000,
    overlap: int | None = None,
    prompt_version: str = "v1.0",
) -> RefinementResult:
    """Refine a full document through chunking and rule-based refinement.

    This is the main entry point for Phase 3A refinement:
    1. Splits raw_text into deterministic chunks
    2. Applies rule-based refinement to each chunk
    3. Preserves raw_text exactly in each chunk
    4. Stores cleaned_text separately
    5. Attaches refinement metadata

    Args:
        document_id: Document identifier
        raw_text: Original document text (preserved exactly)
        chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks (default: 200, or auto-computed if chunk_size <= 200)
        prompt_version: Version identifier for refinement rules

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

    for chunk in chunks:
        # Apply rule-based refinement
        cleaned_text, chunk_metadata = rule_based_refine(
            chunk.raw_text,
            prompt_version=prompt_version,
        )

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
                "created_at": chunk_metadata.created_at,
                "warnings": chunk_metadata.warnings,
                "no_new_facts_checked": chunk_metadata.no_new_facts_checked,
                "source_raw_hash": chunk_metadata.source_raw_hash,
                "raw_text_length": chunk_metadata.raw_text_length,
                "cleaned_text_length": chunk_metadata.cleaned_text_length,
            },
        )
        refined_chunks.append(refined_chunk)

        # Accumulate warnings for document-level metadata
        all_warnings.extend(chunk_metadata.warnings)

    # Compute actual cleaned text length (sum of all refined chunk cleaned_text)
    total_cleaned_chars = sum(len(c.cleaned_text) for c in refined_chunks)

    # Step 3: Build overall metadata
    overall_metadata = RefinementMetadata(
        refinement_method="rule_based",
        prompt_version=prompt_version,
        model_name=None,
        created_at=RefinementMetadata.get_current_timestamp(),
        warnings=list(set(all_warnings)),  # Deduplicate
        no_new_facts_checked=True,
        source_raw_hash=TextChunk.compute_raw_hash(raw_text) if raw_text else None,
        raw_text_length=len(raw_text),  # Document original length
        cleaned_text_length=total_cleaned_chars,  # Actual cleaned output length
    )

    # Step 4: Return result with correct statistics
    return RefinementResult(
        document_id=document_id,
        chunks=refined_chunks,
        metadata=overall_metadata,
        total_chunks=len(refined_chunks),
        total_raw_chars=len(raw_text),  # Document length, not sum of chunks
        total_cleaned_chars=total_cleaned_chars,  # Actual cleaned output length
    )
