"""Directory-level wiki health check.

Scans a directory of exported wiki Markdown notes, runs lint checks
on each file, detects cross-note issues (duplicate note_id), and
produces a deterministic WikiHealthReport.
"""

import json
from pathlib import Path

from tracevault.wiki.lint import lint_note
from tracevault.wiki.parser import extract_frontmatter, parse_wiki_note
from tracevault.wiki.report import (
    IssueSeverity,
    WikiHealthReport,
    WikiLintIssue,
    WikiParsedNote,
)


def check_wiki_health(
    path: Path | str,
    *,
    source_hashes: dict[str, str] | None = None,
) -> WikiHealthReport:
    """Run a full health check on a directory of wiki notes or a single file.

    Args:
        path: Directory containing exported Markdown notes, or a single .md file.
        source_hashes: Optional mapping of document_id -> expected source
            hash for drift detection.

    Returns:
        WikiHealthReport with all issues sorted deterministically
        by (file_path, code, message).
    """
    root = Path(path)

    if root.is_file():
        return _check_single_file(root, source_hashes=source_hashes)

    return _check_directory(root, source_hashes=source_hashes)


def _check_single_file(
    file_path: Path,
    *,
    source_hashes: dict[str, str] | None = None,
) -> WikiHealthReport:
    """Run lint checks on a single Markdown file."""
    issues: list[WikiLintIssue] = []

    if file_path.suffix.lower() != ".md":
        issues.append(WikiLintIssue(
            code="missing_frontmatter",
            severity=IssueSeverity.WARNING,
            message=f"File is not a Markdown file: {file_path.name}",
            file_path=str(file_path),
        ))
        return WikiHealthReport(
            path=str(file_path),
            files_scanned=1,
            issues=issues,
            parsed_notes=[],
        )

    parsed = parse_wiki_note(file_path)
    file_issues = lint_note(parsed, source_hashes=source_hashes)

    return WikiHealthReport(
        path=str(file_path),
        files_scanned=1,
        issues=file_issues,
        parsed_notes=[parsed],
    )


def _check_directory(
    root: Path,
    *,
    source_hashes: dict[str, str] | None = None,
) -> WikiHealthReport:
    """Run a full health check on a directory of wiki notes."""
    md_files = _collect_md_files(root)
    issues: list[WikiLintIssue] = []
    parsed_notes: list[WikiParsedNote] = []
    seen_note_ids: dict[str, str] = {}

    for fp in md_files:
        rel = str(fp)
        parsed = parse_wiki_note(fp)
        parsed_notes.append(parsed)
        file_issues = lint_note(parsed, source_hashes=source_hashes)
        issues.extend(file_issues)

        # Cross-note checks (only for directory scans)
        content = fp.read_text(encoding="utf-8")
        fm_raw, _ = extract_frontmatter(content)
        if fm_raw is not None and fm_raw != "MALFORMED":
            note_id = parsed.frontmatter.get("note_id")
            if note_id:
                prev = seen_note_ids.get(note_id)
                if prev and prev != rel:
                    issues.append(WikiLintIssue(
                        code="duplicate_note_id",
                        severity=IssueSeverity.ERROR,
                        message=(
                            f"Duplicate note_id '{note_id}' in "
                            f"'{prev}' and '{rel}'"
                        ),
                        file_path=rel,
                    ))
                elif not prev:
                    seen_note_ids[note_id] = rel
            else:
                issues.append(WikiLintIssue(
                    code="orphan_note",
                    severity=IssueSeverity.WARNING,
                    message=(
                        "Note has no note_id in frontmatter "
                        "(orphaned or non-TraceVault Markdown)"
                    ),
                    file_path=rel,
                ))
        else:
            issues.append(WikiLintIssue(
                code="orphan_note",
                severity=IssueSeverity.WARNING,
                message="Note has no valid frontmatter (orphaned Markdown file)",
                file_path=rel,
            ))

    # Deterministic ordering: file_path, then code, then message
    issues.sort(key=lambda i: (i.file_path, i.code, i.message))

    return WikiHealthReport(
        path=str(root),
        files_scanned=len(md_files),
        issues=issues,
        parsed_notes=parsed_notes,
    )


def _collect_md_files(root: Path) -> list[Path]:
    """Collect .md files recursively, sorted for determinism.

    Skips hidden directories (starting with . or _).
    """
    files: list[Path] = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if child.name.startswith((".", "_")):
                continue
            files.extend(_collect_md_files(child))
        elif child.suffix.lower() == ".md":
            files.append(child)
    return files


def print_health_report(report: WikiHealthReport, *, as_json: bool = False) -> int:
    """Print a health report and return the appropriate exit code.

    Args:
        report: The WikiHealthReport to display.
        as_json: If True, output JSON.  Otherwise human-readable text.

    Returns:
        0 if no ERROR issues, 1 if any ERROR issues exist.
    """
    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_human_report(report)

    return 1 if report.error_count > 0 else 0


def _print_human_report(report: WikiHealthReport) -> None:
    print(f"Wiki Health Report: {report.path}")
    print(f"Files scanned: {report.files_scanned}")
    print(f"Issues: {report.error_count} error(s), {report.warning_count} warning(s)")
    print(f"Status: {'PASSED' if report.passed else 'FAILED'}")
    print()

    if not report.issues:
        print("No issues found.")
        return

    # Group by file
    by_file: dict[str, list[WikiLintIssue]] = {}
    for issue in report.issues:
        by_file.setdefault(issue.file_path, []).append(issue)

    for fp in sorted(by_file):
        print(f"  {fp}:")
        for issue in by_file[fp]:
            sev = issue.severity.value.upper()
            print(f"    [{sev}] {issue.code}: {issue.message}")
        print()
