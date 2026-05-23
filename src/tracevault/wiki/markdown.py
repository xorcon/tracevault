"""Deterministic Markdown rendering for wiki notes.

Renders WikiNote objects into Markdown strings with:
- Machine-readable YAML frontmatter
- Title
- Summary section (if provided)
- Claims section with claim-to-evidence mapping
- Evidence references section
- TraceVault metadata section
"""

from copy import copy

from tracevault.wiki.models import WikiEvidenceReference, WikiNote


def _merge_refs(refs: list[WikiEvidenceReference]) -> WikiEvidenceReference:
    """Merge multiple evidence refs sharing the same stable identity.

    Produces a single new ref that preserves the richest non-empty
    metadata from any input ref.  Original refs are never mutated.

    The first ref's label is used as the display label for deterministic
    claim-to-evidence mapping.
    """
    if len(refs) == 1:
        return refs[0]

    winner = copy(refs[0])
    for ref in refs[1:]:
        if not winner.source_path and ref.source_path:
            winner.source_path = ref.source_path
        if not winner.source_raw_hash and ref.source_raw_hash:
            winner.source_raw_hash = ref.source_raw_hash
        if not winner.raw_text_hash and ref.raw_text_hash:
            winner.raw_text_hash = ref.raw_text_hash
        if not winner.evidence_text_hash and ref.evidence_text_hash:
            winner.evidence_text_hash = ref.evidence_text_hash
        if not winner.excerpt and ref.excerpt:
            winner.excerpt = ref.excerpt
    return winner


def yaml_scalar(value: object) -> str:
    """Render a Python value as a safe YAML scalar for frontmatter.

    Strings are emitted as double-quoted scalars to prevent YAML-significant
    characters (: # \\ " true false null) from corrupting machine-readable
    metadata.  Numeric types are emitted without quotes.

    Args:
        value: A Python value (str, int, float, bool, or None).

    Returns:
        A YAML-safe scalar string.
    """
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    s = str(value)
    if s == "":
        return '""'
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace(
        "\n", "\\n"
    ).replace("\r", "\\r").replace("\t", "\\t")
    return f'"{escaped}"'


def render_note(note: WikiNote) -> str:
    """Render a WikiNote into a deterministic Markdown string.

    The output format is:
    - YAML frontmatter with proof-chain metadata
    - H1 title
    - Summary paragraph (if non-empty)
    - Claims section with evidence citation mapping
    - Evidence references section
    - TraceVault metadata section

    Args:
        note: The WikiNote to render.

    Returns:
        A Markdown string with YAML frontmatter.
    """
    # Build a deduplicated evidence map keyed by stable identity.
    # If two refs share the same label but differ in identity,
    # the second one gets a disambiguated display label (e.g., E1-2).
    identity_map = _build_identity_map(note)
    display_labels = _resolve_display_labels(identity_map)

    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    _render_frontmatter(note, lines)
    lines.append("---")
    lines.append("")

    # Title
    lines.append(f"# {note.title}")
    lines.append("")

    # Summary (only if non-empty)
    if note.summary:
        lines.append(note.summary)
        lines.append("")

    # Claims section
    lines.append("## Claims")
    lines.append("")
    for claim in note.claims:
        if claim.unsupported:
            lines.append(f"- {claim.statement} *(unsupported — no evidence)*")
        elif not claim.has_evidence:
            # Invalid supported claim — render as unsupported to avoid
            # silently emitting claim [].
            lines.append(
                f"- {claim.statement} *(unsupported — no evidence refs)*"
            )
        else:
            labels = ", ".join(
                _dedup_labels(display_labels, claim.evidence_refs)
            )
            lines.append(f"- {claim.statement} [{labels}]")
    lines.append("")

    # Evidence references section
    lines.append("## Evidence References")
    lines.append("")
    for identity, ref in identity_map:
        display = display_labels[identity]
        lines.append(f"### {display}")
        lines.append("")
        lines.append(f"- **Document**: `{ref.document_id}`")
        lines.append(f"- **Chunk**: `{ref.chunk_id}`")
        if ref.source_path:
            lines.append(f"- **Source**: `{ref.source_path}`")
        if ref.source_raw_hash:
            lines.append(f"- **Source Raw Hash**: `{ref.source_raw_hash}`")
        if ref.raw_text_hash:
            lines.append(f"- **Raw Text Hash**: `{ref.raw_text_hash}`")
        if ref.evidence_text_hash:
            lines.append(f"- **Evidence Text Hash**: `{ref.evidence_text_hash}`")
        if ref.excerpt:
            lines.append("")
            lines.extend(_render_blockquote(ref.excerpt))
        lines.append("")

    # TraceVault metadata section
    lines.append("---")
    lines.append("")
    lines.append("## TraceVault Metadata")
    lines.append("")
    lines.append(f"- note_id: `{note.note_id}`")
    if note.metadata:
        lines.append(
            f"- generated_at: {yaml_scalar(note.metadata.generated_at_iso())}"
        )
        lines.append(
            f"- source_policy: {yaml_scalar(note.metadata.source_policy)}"
        )
        lines.append(
            f"- validation_status: {yaml_scalar(note.metadata.validation_status)}"
        )
        lines.append(f"- evidence_count: {note.metadata.evidence_count}")
        lines.append(
            f"- generator_version: {yaml_scalar(note.metadata.generator_version)}"
        )
        lines.append(
            f"- schema_version: {yaml_scalar(note.metadata.schema_version)}"
        )
        if note.metadata.source_documents:
            lines.append("- source_documents:")
            for sd in note.metadata.source_documents:
                lines.append(
                    f"  - document_id: {yaml_scalar(sd.document_id)}"
                )
        if note.metadata.source_chunks:
            lines.append("- source_chunks:")
            for sc in note.metadata.source_chunks:
                lines.append(f"  - chunk_id: {yaml_scalar(sc.chunk_id)}")
    lines.append("")

    return "\n".join(lines)


def _render_frontmatter(note: WikiNote, lines: list[str]) -> None:
    """Render YAML frontmatter fields in stable order.

    String values are rendered through yaml_scalar() to produce safe
    double-quoted YAML scalars.  Numeric values like evidence_count are
    emitted without quotes.
    """
    meta = note.metadata
    if meta:
        lines.append(f"note_id: {yaml_scalar(meta.note_id)}")
        lines.append(f"note_type: {yaml_scalar(meta.note_type)}")
        lines.append(f"status: {yaml_scalar(meta.status)}")
        lines.append(f"generated_at: {yaml_scalar(meta.generated_at_iso())}")
        lines.append(f"generated_by: {yaml_scalar(meta.generated_by)}")
        lines.append(f"generator_version: {yaml_scalar(meta.generator_version)}")
        lines.append(f"schema_version: {yaml_scalar(meta.schema_version)}")
        lines.append(f"source_policy: {yaml_scalar(meta.source_policy)}")
        lines.append(f"validation_status: {yaml_scalar(meta.validation_status)}")
        if meta.confidence is not None:
            lines.append(f"confidence: {yaml_scalar(meta.confidence)}")
        lines.append(f"evidence_count: {meta.evidence_count}")

        if meta.source_documents:
            lines.append("source_documents:")
            for sd in meta.source_documents:
                lines.append(f"  - document_id: {yaml_scalar(sd.document_id)}")
                if sd.source_path:
                    lines.append(f"    source_path: {yaml_scalar(sd.source_path)}")
                if sd.source_raw_hash:
                    lines.append(
                        f"    source_raw_hash: {yaml_scalar(sd.source_raw_hash)}"
                    )
                if sd.content_hash:
                    lines.append(
                        f"    content_hash: {yaml_scalar(sd.content_hash)}"
                    )

        if meta.source_chunks:
            lines.append("source_chunks:")
            for sc in meta.source_chunks:
                lines.append(f"  - document_id: {yaml_scalar(sc.document_id)}")
                lines.append(f"    chunk_id: {yaml_scalar(sc.chunk_id)}")
                if sc.source_raw_hash:
                    lines.append(
                        f"    source_raw_hash: {yaml_scalar(sc.source_raw_hash)}"
                    )
                if sc.raw_text_hash:
                    lines.append(
                        f"    raw_text_hash: {yaml_scalar(sc.raw_text_hash)}"
                    )
                if sc.cleaned_text_hash:
                    lines.append(
                        f"    cleaned_text_hash: {yaml_scalar(sc.cleaned_text_hash)}"
                    )
                if sc.evidence_text_hash:
                    lines.append(
                        f"    evidence_text_hash: {yaml_scalar(sc.evidence_text_hash)}"
                    )


def _build_identity_map(
    note: WikiNote,
) -> list[tuple[tuple, WikiEvidenceReference]]:
    """Build an ordered list of (identity_key, merged_ref) pairs.

    Collects all refs from claims and source_evidence, groups by stable
    identity, and merges duplicates into a single richer ref per identity.
    Claim refs are processed first to preserve ordering.
    """
    groups: dict[tuple, list[WikiEvidenceReference]] = {}
    order: list[tuple] = []

    def _add(ref: WikiEvidenceReference) -> None:
        key = ref.identity_key()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(ref)

    for claim in note.claims:
        for ref in claim.evidence_refs:
            _add(ref)

    for ref in note.source_evidence:
        _add(ref)

    return [(key, _merge_refs(groups[key])) for key in order]


def _dedup_labels(
    display_labels: dict[tuple, str],
    refs: list[WikiEvidenceReference],
) -> list[str]:
    """Resolve citation labels for a claim's evidence refs, deduplicating.

    When two refs share the same stable identity (e.g., a sparse claim ref
    and a full source_evidence ref), they map to the same display label.
    This helper preserves order while removing duplicate label occurrences.
    """
    seen: set[str] = set()
    labels: list[str] = []
    for ref in refs:
        label = display_labels[ref.identity_key()]
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def _resolve_display_labels(
    identity_map: list[tuple[tuple, WikiEvidenceReference]],
) -> dict[tuple, str]:
    """Resolve globally unique display labels for each identity key.

    If two refs share the same original label but differ in identity,
    the first keeps the original label, subsequent ones get a
    deterministic disambiguation suffix (e.g., E1-2).

    A global set of used labels and a pre-collected set of original
    labels ensure a disambiguated candidate (e.g., E1-2) never collides
    with another ref's original label, and vice versa.
    """
    # Pre-collect all original labels so disambiguation can skip them.
    originals: set[str] = {ref.label for _, ref in identity_map}

    used_labels: set[str] = set()
    label_count: dict[str, int] = {}
    result: dict[tuple, str] = {}

    for identity, ref in identity_map:
        original = ref.label
        if original not in label_count:
            label_count[original] = 1
            if original not in used_labels:
                result[identity] = original
                used_labels.add(original)
            else:
                count = 2
                while f"{original}-{count}" in used_labels:
                    count += 1
                result[identity] = f"{original}-{count}"
                used_labels.add(result[identity])
        else:
            label_count[original] += 1
            count = label_count[original]
            candidate = f"{original}-{count}"
            while candidate in used_labels or (
                candidate in originals and candidate != original
            ):
                count += 1
                candidate = f"{original}-{count}"
            result[identity] = candidate
            used_labels.add(candidate)

    return result


def _render_blockquote(text: str) -> list[str]:
    """Render a multi-line excerpt as properly quoted Markdown blockquote lines.

    Every line of the excerpt receives a "> " prefix so that none of the
    excerpt text bleeds into normal body paragraphs.  Blank lines inside
    the excerpt render as ">" to preserve paragraph structure within the
    quote.

    If the excerpt is non-empty but contains no newlines (single-line),
    it returns a single "> line" entry.
    """
    lines = text.splitlines()
    if not lines and text:
        lines = [text]
    return [f"> {line}" if line else ">" for line in lines]
