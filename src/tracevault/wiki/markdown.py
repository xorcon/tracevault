"""Deterministic Markdown rendering for wiki notes.

Renders WikiNote objects into Markdown strings with:
- Machine-readable YAML frontmatter
- Title
- Summary section (if provided)
- Claims section with claim-to-evidence mapping
- Evidence references section
- TraceVault metadata section
"""

from tracevault.wiki.models import WikiEvidenceReference, WikiNote


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
                f"- {claim.statement} *(unsupported — no evidence refs)"
            )
        else:
            labels = ", ".join(
                display_labels[ref.identity_key()]
                for ref in claim.evidence_refs
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
            lines.append(f"> {ref.excerpt}")
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
        if meta.confidence:
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
    """Build an ordered list of (identity_key, ref) pairs.

    Deduplicates by stable identity (document_id, chunk_id, hashes, label),
    not just label. Claim refs come first, then source_evidence.
    """
    seen: set[tuple] = set()
    pairs: list[tuple[tuple, WikiEvidenceReference]] = []

    for claim in note.claims:
        for ref in claim.evidence_refs:
            key = ref.identity_key()
            if key not in seen:
                seen.add(key)
                pairs.append((key, ref))

    for ref in note.source_evidence:
        key = ref.identity_key()
        if key not in seen:
            seen.add(key)
            pairs.append((key, ref))

    return pairs


def _resolve_display_labels(
    identity_map: list[tuple[tuple, WikiEvidenceReference]],
) -> dict[tuple, str]:
    """Resolve display labels for each identity key.

    If two refs share the same original label but differ in identity,
    the first keeps the original label, subsequent ones get a
    deterministic disambiguation suffix (e.g., E1-2).
    """
    label_count: dict[str, int] = {}
    result: dict[tuple, str] = {}

    for identity, ref in identity_map:
        original = ref.label
        if original not in label_count:
            label_count[original] = 1
            result[identity] = original
        else:
            label_count[original] += 1
            result[identity] = f"{original}-{label_count[original]}"

    return result
