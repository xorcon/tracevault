"""Markdown and YAML frontmatter parser for exported wiki notes.

Reads Markdown files produced by Phase 6A wiki export and extracts:
- YAML frontmatter as a dict
- Evidence section headings
- Claim-to-citation mapping

Fail-closed on malformed frontmatter: returns an error indicator so
the linter can emit a structured issue.
"""

import re
from pathlib import Path

from tracevault.wiki.report import WikiParsedNote


def extract_frontmatter(markdown: str) -> tuple[str | None, str | None]:
    """Extract YAML frontmatter from a Markdown string.

    Returns:
        (frontmatter_string, body) if delimiters found.
        (None, full_text) if no opening delimiter.
        ("MALFORMED", remaining) if opening without closing.
    """
    stripped = markdown.lstrip("\n\r")
    if not stripped.startswith("---"):
        return None, markdown

    rest = stripped[3:]
    close_idx = rest.find("\n---")
    if close_idx == -1:
        return "MALFORMED", rest

    return rest[:close_idx].strip(), rest[close_idx + 4:]


def parse_yaml_frontmatter(raw: str) -> dict:
    """Parse YAML frontmatter into a dict.

    Supports:
    - Double-quoted strings with standard YAML escapes
    - Bare strings
    - booleans, integers, floats, null
    - Nested mappings and sequences (limited, for source_documents/chunks)

    Raises:
        ValueError: If the YAML cannot be parsed (fail-closed).
    """
    try:
        import yaml  # type: ignore[import-not-found]

        try:
            result = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML parse error: {exc}") from exc

        if not isinstance(result, dict):
            raise ValueError("frontmatter root is not a mapping")
        return result
    except ImportError:
        pass

    result = _simple_yaml_parse(raw)
    if result is None:
        raise ValueError("failed to parse YAML frontmatter")
    return result


# ---------------------------------------------------------------------------
# Minimal YAML parser (no external dependency)
# ---------------------------------------------------------------------------

def _simple_yaml_parse(text: str) -> dict | None:
    """Minimal YAML parser for the subset produced by the wiki exporter.

    Returns None on unrecoverable parse failure.
    """
    result: dict = {}
    current_key = None
    current_value = None
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0:
            if current_key is not None:
                result[current_key] = current_value
                current_key = None
                current_value = None

            kv = _parse_kv(stripped)
            if kv is None:
                return None
            key, value = kv

            if value is _SENTINEL:
                current_key = key
                current_value = []
                if isinstance(value, _SENTINEL_TYPE):
                    pass
            elif isinstance(value, list):
                result[key] = value
            else:
                result[key] = value
            i += 1
            continue

        if current_key is not None:
            item = _parse_list_item(stripped)
            if item is not None:
                if not isinstance(current_value, list):
                    current_value = []
                current_value.append(item)
                i += 1
                continue

        return None

    if current_key is not None:
        result[current_key] = current_value

    return result


class _SENTINEL_TYPE:
    pass


_SENTINEL = _SENTINEL_TYPE()


def _parse_kv(line: str) -> tuple[str, object] | None:
    colon_idx = line.find(":")
    if colon_idx == -1:
        return None
    key = line[:colon_idx].strip()
    rest = line[colon_idx + 1:].strip()
    if not rest:
        return key, _SENTINEL
    return key, _parse_value(rest)


def _parse_list_item(line: str) -> dict | None:
    if not line.startswith("- "):
        return None
    item_content = line[2:].strip()
    items = []
    for part in item_content.split():
        kv = _parse_kv(part)
        if kv:
            items.append(kv)
    if not items:
        kv = _parse_kv(item_content)
        if kv:
            items = [kv]
    return dict(items) if items else {}


def _parse_value(raw: str) -> object:
    if raw.startswith('"'):
        end = 1
        result = []
        while end < len(raw):
            if raw[end] == "\\" and end + 1 < len(raw):
                ch = raw[end + 1]
                escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
                result.append(escapes.get(ch, ch))
                end += 2
                continue
            if raw[end] == '"':
                return "".join(result)
            result.append(raw[end])
            end += 1
        raise ValueError(f"unterminated quoted string: {raw[:40]}")
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null" or raw == "~":
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# ---------------------------------------------------------------------------
# Public parsing API
# ---------------------------------------------------------------------------

EVIDENCE_HEADING_RE = re.compile(r"^### (.+)$")
CLAIM_CITATION_RE = re.compile(r"^- (.+?)\s+\[([^\]]+)\]$")


def parse_wiki_note(file_path: Path | str) -> WikiParsedNote:
    """Parse a single exported wiki Markdown note.

    Args:
        file_path: Path to the Markdown file.

    Returns:
        WikiParsedNote with extracted frontmatter and body structure.
        The frontmatter dict may be empty if frontmatter is missing/malformed.
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")

    frontmatter_raw, body = extract_frontmatter(content)
    parsed_fm: dict = {}
    raw_fm_str = ""
    yaml_parse_error = False

    if frontmatter_raw is not None and frontmatter_raw != "MALFORMED":
        raw_fm_str = frontmatter_raw
        try:
            parsed_fm = parse_yaml_frontmatter(frontmatter_raw)
        except ValueError:
            parsed_fm = {}
            yaml_parse_error = True
        # Extract body even when frontmatter YAML is parse-error
        # (extract_frontmatter already gave us the body for valid delimiters)

    evidence_labels = _extract_evidence_labels(body or "")
    claim_citations = _extract_claim_citations(body or "")

    return WikiParsedNote(
        file_path=str(path),
        frontmatter=parsed_fm,
        raw_frontmatter=raw_fm_str,
        body=body or "",
        evidence_labels=evidence_labels,
        claim_citations=claim_citations,
        yaml_parse_error=yaml_parse_error,
    )


def _extract_evidence_labels(body: str) -> list[str]:
    """Extract evidence section headings (### Label) from the body."""
    labels: list[str] = []
    in_evidence_section = False

    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_evidence_section = stripped == "## Evidence References"
            continue
        if in_evidence_section and stripped.startswith("### "):
            labels.append(stripped[4:])

    return labels


def _extract_claim_citations(body: str) -> list[tuple[str, list[str]]]:
    """Extract claim-to-citation pairs from the Claims section.

    Returns:
        Ordered list of (claim_text, [citation_labels]) pairs, one per
        claim line.  Duplicate claim text produces separate entries so
        all citation labels are preserved.
    """
    citations: list[tuple[str, list[str]]] = []
    in_claims = False

    for line in body.split("\n"):
        stripped = line.strip()
        if stripped == "## Claims":
            in_claims = True
            continue
        if in_claims and stripped.startswith("## "):
            break
        if in_claims:
            match = CLAIM_CITATION_RE.match(stripped)
            if match:
                statement = match.group(1)
                labels = [token.strip() for token in match.group(2).split(",")]
                citations.append((statement, labels))

    return citations
