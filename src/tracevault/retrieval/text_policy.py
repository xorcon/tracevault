"""Text retrieval policy application.

Applies TextRetrievalPolicy to control which text fields are used
for search. Does NOT affect result text — raw_text is always preserved.
"""

from tracevault.retrieval.models import CandidateEvidence, TextRetrievalPolicy


def get_search_text(
    candidate: CandidateEvidence,
    policy: TextRetrievalPolicy,
) -> str:
    """Get the text to search based on the text policy.

    For DUAL_CONTEXT, returns both raw_text and cleaned_text concatenated.
    For RAW_ONLY, returns only raw_text.
    For CLEANED_ONLY, returns only cleaned_text.

    This affects search text selection only — it does NOT modify the
    candidate or remove raw_text from results.
    """
    if policy.mode == "RAW_ONLY":
        return candidate.raw_text
    elif policy.mode == "CLEANED_ONLY":
        return candidate.cleaned_text
    else:  # DUAL_CONTEXT
        return candidate.raw_text + " " + candidate.cleaned_text
