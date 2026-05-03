"""Text retrieval policy application.

Applies TextRetrievalPolicy to control which text fields are used
for indexing and which are preserved in results.
"""

from tracevault.retrieval.models import CandidateEvidence, TextRetrievalPolicy


def get_search_text(
    candidate: CandidateEvidence,
    policy: TextRetrievalPolicy,
) -> str:
    """Get the text to search based on the text policy.

    For DUAL_CONTEXT, returns both raw_text and cleaned_text concatenated
    for keyword matching purposes.
    """
    if policy.mode == "RAW_ONLY":
        return candidate.raw_text
    elif policy.mode == "CLEANED_ONLY":
        return candidate.cleaned_text
    else:  # DUAL_CONTEXT
        return candidate.raw_text + " " + candidate.cleaned_text


def apply_text_policy(
    candidates: list[CandidateEvidence],
    policy: TextRetrievalPolicy,
) -> list[CandidateEvidence]:
    """Apply text policy to candidates, preserving only allowed text fields.

    For RAW_ONLY: set cleaned_text to empty string in results
    For CLEANED_ONLY: set raw_text to empty string in results
    For DUAL_CONTEXT: preserve both

    Does NOT modify the original candidate objects.
    """
    result = []
    for c in candidates:
        new_candidate = CandidateEvidence(
            document_id=c.document_id,
            chunk_id=c.chunk_id,
            chunk_index=c.chunk_index,
            source_path=c.source_path,
            source_type=c.source_type,
            raw_text=c.raw_text if policy.preserves_raw() else "",
            cleaned_text=c.cleaned_text if policy.preserves_cleaned() else "",
            raw_text_hash=c.raw_text_hash,
            cleaned_text_hash=c.cleaned_text_hash,
            score=c.score,
            trace=c.trace,
            metadata=c.metadata,
        )
        result.append(new_candidate)
    return result
