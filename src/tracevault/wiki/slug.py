"""Deterministic slug generation for wiki note filenames.

Slugs are filename-safe, lowercase, hyphen-separated strings derived
from note titles.
"""

import re


def generate_slug(title: str) -> str:
    """Generate a deterministic, filename-safe slug from a title.

    Steps:
    1. Lowercase
    2. Replace whitespace/runs of special chars with single hyphen
    3. Strip leading/trailing hyphens
    4. Fallback to "note" if empty

    Args:
        title: The note title to slugify.

    Returns:
        A filename-safe slug string.
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "note"
