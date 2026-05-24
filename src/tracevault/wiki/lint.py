"""Single-note lint checks for exported wiki Markdown.

Each check function takes a WikiParsedNote and returns a list of
WikiLintIssue objects.  The main ``lint_note()`` orchestrates all
checks deterministically.

All checks are read-only: they never mutate the parsed note.
"""

import re
from dataclasses import dataclass

from tracevault.wiki.parser import extract_frontmatter
from tracevault.wiki.report import (
    IssueSeverity,
    WikiLintIssue,
    WikiParsedNote,
)

VALID_NOTE_TYPES = frozenset({"compiled_knowledge_wiki_note"})
VALID_SCHEMA_VERSIONS = frozenset({"wiki-export-v1"})
VALID_STATUSES = frozenset({"proposal", "published", "draft", "deprecated"})
VALID_SOURCE_POLICY = "raw_text_authoritative"

_VALIDATION_STATUS_VALID = frozenset({"validated"})
_VALIDATION_STATUS_ALLOWED = frozenset({"validated", "validation_required"})

REQUIRED_FIELDS = [
    "note_id",
    "note_type",
    "schema_version",
    "status",
    "generated_by",
    "source_policy",
    "validation_status",
    "evidence_count",
]


@dataclass
class _EvidenceEntry:
    """Internal representation of a parsed evidence section entry."""
    label: str
    has_document_id: bool = False
    has_chunk_id: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_note(
    note: WikiParsedNote,
    *,
    source_hashes: dict[str, str] | None = None,
) -> list[WikiLintIssue]:
    """Run all lint checks on a single parsed wiki note.

    Args:
        note: Parsed wiki note from ``parse_wiki_note()``.
        source_hashes: Optional mapping of document_id -> expected source
            hash.  When provided, source hash mismatch checks are enabled.

    Returns:
        Deterministic list of lint issues (empty means clean).
    """
    import pathlib

    issues: list[WikiLintIssue] = []
    fp = note.file_path

    content = pathlib.Path(fp).read_text(encoding="utf-8")
    fm_raw, _body = extract_frontmatter(content)

    # --- Frontmatter existence checks (early return) ---
    if fm_raw is None:
        return [WikiLintIssue(
            code="missing_frontmatter",
            severity=IssueSeverity.ERROR,
            message="No YAML frontmatter (missing opening --- delimiter)",
            file_path=fp,
        )]

    if fm_raw == "MALFORMED":
        return [WikiLintIssue(
            code="malformed_frontmatter",
            severity=IssueSeverity.ERROR,
            message="YAML frontmatter has no closing --- delimiter",
            file_path=fp,
        )]

    if note.yaml_parse_error:
        return [WikiLintIssue(
            code="malformed_frontmatter",
            severity=IssueSeverity.ERROR,
            message="YAML frontmatter contains parse errors",
            file_path=fp,
        )]

    fm = note.frontmatter
    body = note.body or ""

    # --- Required field checks ---
    for fname in REQUIRED_FIELDS:
        val = fm.get(fname)
        if val is None or (isinstance(val, str) and not val.strip()):
            issues.append(WikiLintIssue(
                code="missing_required_field",
                severity=IssueSeverity.ERROR,
                message=f"Missing required frontmatter field: {fname}",
                file_path=fp,
            ))

    # --- Value validation ---
    _check_enum_field(fm, "note_type", VALID_NOTE_TYPES, fp, issues)
    _check_enum_field(fm, "schema_version", VALID_SCHEMA_VERSIONS, fp, issues)
    _check_enum_field(fm, "status", VALID_STATUSES, fp, issues)
    _check_source_policy(fm, fp, issues)
    _check_validation_status(fm, fp, issues)

    # --- Evidence count consistency ---
    _check_evidence_count(fm, body, fp, issues)

    # --- Claim citation checks ---
    _check_claims_have_citations(note, issues)
    _check_citations_resolve(note, issues)

    # --- Evidence reference checks ---
    entries = _parse_evidence_entries(body)
    _check_evidence_labels_unique(entries, fp, issues)
    _check_evidence_source_identity(entries, fp, issues)

    # --- Source hash checks (optional) ---
    if source_hashes is not None:
        _check_source_hashes(fm, body, source_hashes, fp, issues)

    # --- TraceVault metadata section ---
    _check_tracevault_metadata(body, fp, issues)

    return issues


# ---------------------------------------------------------------------------
# Field-level validators
# ---------------------------------------------------------------------------


def _check_enum_field(
    fm: dict,
    name: str,
    valid: frozenset,
    fp: str,
    issues: list[WikiLintIssue],
) -> None:
    code_map = {
        "note_type": "invalid_note_type",
        "schema_version": "invalid_schema_version",
        "status": "invalid_status",
    }
    val = fm.get(name)
    if val is not None and str(val) not in valid:
        issues.append(WikiLintIssue(
            code=code_map[name],  # type: ignore[literal-required]
            severity=IssueSeverity.ERROR,
            message=f"Invalid {name}: {val!r} (expected one of {sorted(valid)})",
            file_path=fp,
        ))


def _check_source_policy(fm: dict, fp: str, issues: list[WikiLintIssue]) -> None:
    val = fm.get("source_policy")
    if val is not None and str(val) != VALID_SOURCE_POLICY:
        issues.append(WikiLintIssue(
            code="invalid_source_policy",
            severity=IssueSeverity.ERROR,
            message=(
                f"Invalid source_policy: {val!r} "
                f"(expected '{VALID_SOURCE_POLICY}')"
            ),
            file_path=fp,
        ))


def _check_validation_status(
    fm: dict, fp: str, issues: list[WikiLintIssue]
) -> None:
    val = fm.get("validation_status")
    if val is None:
        return
    s = str(val)
    if s in _VALIDATION_STATUS_VALID:
        return
    if s in _VALIDATION_STATUS_ALLOWED:
        issues.append(WikiLintIssue(
            code="invalid_validation_status",
            severity=IssueSeverity.WARNING,
            message=(
                f"validation_status is '{s}' "
                f"(only 'validated' passes cleanly)"
            ),
            file_path=fp,
        ))
        return
    issues.append(WikiLintIssue(
        code="invalid_validation_status",
        severity=IssueSeverity.ERROR,
        message=f"Invalid validation_status: {val!r}",
        file_path=fp,
    ))


# ---------------------------------------------------------------------------
# Evidence and citation checks
# ---------------------------------------------------------------------------


def _check_evidence_count(fm: dict, body: str, fp: str, issues: list[WikiLintIssue]) -> None:
    expected = fm.get("evidence_count")
    if expected is None:
        return
    try:
        expected_n = int(expected)
    except (ValueError, TypeError):
        return

    actual_n = _count_evidence_headings(body)
    if expected_n != actual_n:
        issues.append(WikiLintIssue(
            code="evidence_count_mismatch",
            severity=IssueSeverity.ERROR,
            message=(
                f"evidence_count is {expected_n} but found {actual_n} "
                f"evidence section(s) in body"
            ),
            file_path=fp,
        ))


CLAIM_LINE_RE = re.compile(r"^- (.+)$")
CITATION_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
UNUPPORTED_RE = re.compile(r"\(unsupported", re.IGNORECASE)


def _check_claims_have_citations(note: WikiParsedNote, issues: list[WikiLintIssue]) -> None:
    """Every supported claim line must have at least one [citation]."""
    in_claims = False
    for line in (note.body or "").split("\n"):
        stripped = line.strip()
        if stripped == "## Claims":
            in_claims = True
            continue
        if in_claims and stripped.startswith("## "):
            break
        if not in_claims or not stripped.startswith("- "):
            continue
        content = stripped[2:]
        if UNUPPORTED_RE.search(content):
            continue
        if not CITATION_BRACKET_RE.search(content):
            issues.append(WikiLintIssue(
                code="claim_missing_citation",
                severity=IssueSeverity.ERROR,
                message=f"Supported claim has no evidence citation: {content[:80]!r}",
                file_path=note.file_path,
            ))


def _check_citations_resolve(note: WikiParsedNote, issues: list[WikiLintIssue]) -> None:
    """Every citation label in claims must resolve to an evidence heading."""
    evidence_set = set(note.evidence_labels)
    for _statement, citations in note.claim_citations.items():
        for cit in citations:
            if cit not in evidence_set:
                issues.append(WikiLintIssue(
                    code="citation_unresolved",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"Citation [{cit}] in claim is not found in "
                        f"evidence references"
                    ),
                    file_path=note.file_path,
                ))


def _parse_evidence_entries(body: str) -> list[_EvidenceEntry]:
    """Parse evidence section entries from the Markdown body."""
    entries: list[_EvidenceEntry] = []
    in_section = False
    current: _EvidenceEntry | None = None

    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped == "## Evidence References":
                in_section = True
            else:
                if current is not None:
                    entries.append(current)
                    current = None
                in_section = False
            continue
        if not in_section:
            continue
        if stripped.startswith("### "):
            if current is not None:
                entries.append(current)
            current = _EvidenceEntry(label=stripped[4:])
        elif current is not None:
            if re.search(r"\*\*Document\*\*:", stripped):
                current.has_document_id = bool(
                    re.search(r"`[^`]+`", stripped)
                )
            if re.search(r"\*\*Chunk\*\*:", stripped):
                current.has_chunk_id = bool(
                    re.search(r"`[^`]+`", stripped)
                )

    if current is not None:
        entries.append(current)
    return entries


def _check_evidence_labels_unique(
    entries: list[_EvidenceEntry], fp: str, issues: list[WikiLintIssue]
) -> None:
    seen: dict[str, int] = {}
    for e in entries:
        seen[e.label] = seen.get(e.label, 0) + 1
    for label, count in sorted(seen.items()):
        if count > 1:
            issues.append(WikiLintIssue(
                code="duplicate_evidence_label",
                severity=IssueSeverity.ERROR,
                message=f"Evidence label '{label}' appears {count} times",
                file_path=fp,
            ))


def _check_evidence_source_identity(
    entries: list[_EvidenceEntry], fp: str, issues: list[WikiLintIssue]
) -> None:
    for e in entries:
        if not e.has_document_id:
            issues.append(WikiLintIssue(
                code="evidence_missing_document_id",
                severity=IssueSeverity.ERROR,
                message=f"Evidence '{e.label}' is missing document_id",
                file_path=fp,
            ))
        if not e.has_chunk_id:
            issues.append(WikiLintIssue(
                code="evidence_missing_chunk_id",
                severity=IssueSeverity.ERROR,
                message=f"Evidence '{e.label}' is missing chunk_id",
                file_path=fp,
            ))


# ---------------------------------------------------------------------------
# Source hash checks
# ---------------------------------------------------------------------------


DOC_ID_RE = re.compile(r"- \*\*Document\*\*: `([^`]+)`")
SRC_HASH_RE = re.compile(r"- \*\*Source Raw Hash\*\*: `([^`]+)`")


def _check_source_hashes(
    fm: dict,
    body: str,
    source_hashes: dict[str, str],
    fp: str,
    issues: list[WikiLintIssue],
) -> None:
    """Check source hash consistency against a provided source manifest.

    Each note-source entry is stored as (lookup_key, note_hash, display_info).
    The lookup key is source_path (primary) or document_id (fallback for
    simple/custom schemas that lack source_path).
    """
    # list of (lookup_key, note_hash, display_info)
    entries: list[tuple[str, str, str]] = []

    # From body evidence sections (document_id-based, no source_path available)
    in_evidence = False
    current_doc: str | None = None
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_evidence = stripped == "## Evidence References"
            continue
        if stripped.startswith("### "):
            current_doc = None
            continue
        if not in_evidence:
            continue
        m = DOC_ID_RE.match(stripped)
        if m:
            current_doc = m.group(1)
        m = SRC_HASH_RE.match(stripped)
        if m and current_doc:
            entries.append((current_doc, m.group(1), f"document_id='{current_doc}'"))

    # From frontmatter source_documents
    source_docs = fm.get("source_documents")
    if isinstance(source_docs, list):
        for doc in source_docs:
            if isinstance(doc, dict):
                did = doc.get("document_id")
                spath = doc.get("source_path")
                dhash = doc.get("content_hash") or doc.get("source_raw_hash")
                if not dhash:
                    continue
                # Use source_path as primary key (matches real ingestion manifest)
                if spath:
                    info = f"source_path='{spath}'"
                    if did:
                        info += f" document_id='{did}'"
                    entries.append((str(spath), str(dhash), info))
                elif did:
                    # document_id fallback for simple/custom manifests
                    entries.append((str(did), str(dhash), f"document_id='{did}'"))

    # Deduplicate by lookup key, keeping last occurrence
    seen: dict[str, tuple[str, str]] = {}
    for key, nh, info in entries:
        seen[key] = (nh, info)

    for key in sorted(seen):
        note_hash, display_info = seen[key]
        if key not in source_hashes:
            issues.append(WikiLintIssue(
                code="source_hash_missing_expected",
                severity=IssueSeverity.WARNING,
                message=(
                    f"Source {display_info} not found in provided "
                    f"source manifest"
                ),
                file_path=fp,
            ))
        elif source_hashes[key] != note_hash:
            issues.append(WikiLintIssue(
                code="source_hash_mismatch",
                severity=IssueSeverity.WARNING,
                message=(
                    f"Source {display_info} hash mismatch: "
                    f"note='{note_hash}', manifest='{source_hashes[key]}'"
                ),
                file_path=fp,
            ))


# ---------------------------------------------------------------------------
# Body structure checks
# ---------------------------------------------------------------------------


def _count_evidence_headings(body: str) -> int:
    count = 0
    in_section = False
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## Evidence References"
            continue
        if in_section and stripped.startswith("### "):
            count += 1
    return count


def _check_tracevault_metadata(body: str, fp: str, issues: list[WikiLintIssue]) -> None:
    if "## TraceVault Metadata" not in body:
        issues.append(WikiLintIssue(
            code="missing_tracevault_metadata",
            severity=IssueSeverity.ERROR,
            message="Body is missing '## TraceVault Metadata' section",
            file_path=fp,
        ))
