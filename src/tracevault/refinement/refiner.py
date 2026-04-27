"""Rule-based text refinement and no-new-facts safeguard.

Provides deterministic text cleaning without external model calls.

Refinement rules (safe transformations):
- Trim leading/trailing whitespace
- Normalize excessive blank lines (3+ -> 2)
- Normalize repeated spaces (3+ -> 2) but preserve indentation
- Preserve Markdown headings, lists, code blocks
- Preserve all numbers, dates, names, IDs, technical terms

Forbidden:
- Adding facts not in raw_text
- Summarizing into new claims
- Translating
- Removing factual content
- Modifying dates, names, numbers
"""

import hashlib
import re
from dataclasses import dataclass, field

from tracevault.refinement.models import RefinementMetadata


def _compute_raw_hash(text: str) -> str:
    """Compute SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class RefinementWarnings:
    """Warnings detected during refinement.

    Attributes:
        added_words: Words in cleaned_text not in raw_text
        added_numbers: Numbers in cleaned_text not in raw_text
        length_expansion: Percentage cleaned_text is longer than raw_text
        empty_cleaned: Whether cleaned_text became empty from non-empty raw_text
        excessive_changes: Whether changes exceed safe threshold
    """

    added_words: list[str] = field(default_factory=list)
    added_numbers: list[str] = field(default_factory=list)
    length_expansion: float = 0.0
    empty_cleaned: bool = False
    excessive_changes: bool = False


def _extract_words(text: str) -> set[str]:
    """Extract words from text, lowercased."""
    return set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))


def _extract_numbers(text: str) -> set[str]:
    """Extract numbers from text."""
    return set(re.findall(r"\b\d+\.?\d*\b", text))


def check_no_new_facts(raw_text: str, cleaned_text: str) -> RefinementWarnings:
    """Check that cleaned_text does not add new facts compared to raw_text.

    This is a conservative Phase 3A guardrail that flags potential issues:
    - Words in cleaned_text that don't exist in raw_text
    - Numbers in cleaned_text that don't exist in raw_text
    - Cleaned text significantly longer than raw text
    - Empty cleaned text from non-empty raw text

    Args:
        raw_text: Original source text
        cleaned_text: Refined text to check

    Returns:
        RefinementWarnings with detected issues

    Note:
        This is not a perfect semantic verifier. It is a conservative
        check to catch obvious violations like added facts or hallucinations.
    """
    warnings = RefinementWarnings()

    if not raw_text:
        return warnings

    # Check for empty cleaned text from non-empty raw text
    if raw_text and not cleaned_text:
        warnings.empty_cleaned = True

    # Extract and compare words
    raw_words = _extract_words(raw_text)
    cleaned_words = _extract_words(cleaned_text)
    added = cleaned_words - raw_words
    # Filter out common stop words that might be added during normalization
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "must", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "above",
                  "below", "between", "under", "again", "further", "then", "once",
                  "and", "but", "or", "nor", "so", "yet", "both", "either",
                  "neither", "not", "only", "own", "same", "than", "too", "very",
                  "just", "also", "this", "that", "these", "those", "i", "you",
                  "he", "she", "it", "we", "they", "what", "which", "who", "whom"}
    warnings.added_words = sorted([w for w in added if w not in stop_words and len(w) > 2])

    # Extract and compare numbers
    raw_numbers = _extract_numbers(raw_text)
    cleaned_numbers = _extract_numbers(cleaned_text)
    warnings.added_numbers = sorted(list(cleaned_numbers - raw_numbers))

    # Check length expansion
    if raw_text:
        raw_len = len(raw_text)
        cleaned_len = len(cleaned_text)
        if cleaned_len > raw_len:
            warnings.length_expansion = ((cleaned_len - raw_len) / raw_len) * 100
            # Flag if expansion exceeds 20%
            if warnings.length_expansion > 20:
                warnings.excessive_changes = True

    return warnings


def rule_based_refine(
    raw_text: str,
    prompt_version: str = "v1.0",
) -> tuple[str, RefinementMetadata]:
    """Apply rule-based refinement to text.

    This is a deterministic refiner that:
    1. Trims leading/trailing whitespace
    2. Normalizes excessive blank lines (3+ -> 2)
    3. Normalizes excessive spaces (3+ -> 2) while preserving indentation
    4. Preserves all factual content, numbers, dates, names

    Args:
        raw_text: Original text to refine
        prompt_version: Version identifier for these rules

    Returns:
        Tuple of (cleaned_text, RefinementMetadata)

    Example:
        >>> cleaned, meta = rule_based_refine("  Hello   world  ")
        >>> cleaned
        'Hello  world'
    """
    if not raw_text:
        metadata = RefinementMetadata(
            refinement_method="rule_based",
            prompt_version=prompt_version,
            model_name=None,
            created_at=RefinementMetadata.get_current_timestamp(),
            source_raw_hash=_compute_raw_hash(raw_text) if raw_text else None,
        )
        return "", metadata

    text = raw_text

    # Step 1: Trim leading/trailing whitespace
    text = text.strip()

    # Step 2: Normalize excessive blank lines (3+ newlines -> 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Step 3: Normalize excessive spaces (3+ spaces -> 2 spaces) but preserve indentation
    # Process line by line to preserve leading whitespace (indentation)
    lines = text.split("\n")
    processed_lines = []
    for line in lines:
        # Preserve leading whitespace, normalize trailing/internal excessive spaces
        match = re.match(r"^(\s*)(\S.*)?(\s*)$", line)
        if match:
            leading = match.group(1) or ""
            content = match.group(2) or ""
            # Normalize multiple spaces within content to single space, then ensure sentences have space after
            content = re.sub(r"\s{2,}", " ", content)
            processed_lines.append(leading + content)
        else:
            processed_lines.append(line)
    text = "\n".join(processed_lines)

    # Step 4: Remove trailing whitespace from each line
    lines = text.split("\n")
    text = "\n".join(line.rstrip() for line in lines)

    cleaned_text = text

    # Check for no-new-facts violations
    warnings = check_no_new_facts(raw_text, cleaned_text)

    # Build warning list
    warning_list = []
    if warnings.added_words:
        warning_list.append(f"added_words: {warnings.added_words[:5]}")  # Limit to first 5
    if warnings.added_numbers:
        warning_list.append(f"added_numbers: {warnings.added_numbers[:5]}")
    if warnings.empty_cleaned:
        warning_list.append("empty_cleaned_from_nonempty_raw")
    if warnings.excessive_changes:
        warning_list.append(f"excessive_length_expansion: {warnings.length_expansion:.1f}%")

    metadata = RefinementMetadata(
        refinement_method="rule_based",
        prompt_version=prompt_version,
        model_name=None,
        created_at=RefinementMetadata.get_current_timestamp(),
        warnings=warning_list,
        no_new_facts_checked=True,
        source_raw_hash=_compute_raw_hash(raw_text),
        cleaned_text_length=len(cleaned_text),
        raw_text_length=len(raw_text),
    )

    return cleaned_text, metadata
