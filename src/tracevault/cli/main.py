"""TraceVault CLI - Traceable Enterprise Knowledge Reasoning System.

Usage:
    python -m tracevault --help
    python -m tracevault version
    python -m tracevault diagnose
"""

import argparse
import json
import sys
from pathlib import Path

from tracevault import __version__
from tracevault.ingestion import DEFAULT_MANIFEST_PATH, ingest_path
from tracevault.ingestion.manifest import ManifestCorruptionError


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="tracevault",
        description=(
            "TraceVault: Traceable Enterprise Knowledge Reasoning System. "
            "Grounded RAG with hybrid retrieval, source traceability, and audit-ready answers."
        ),
        epilog=(
            "\nArchitecture: https://github.com/xorcon/tracevault/tree/main/docs\n"
            "Foundation milestone: documentation-to-code setup"
        ),
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"TraceVault {__version__}",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show detailed version information",
        description="Display TraceVault version and build information",
    )
    version_parser.add_argument(
        "--brief",
        action="store_true",
        help="Show only version number",
    )

    # Diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Run diagnostic checks",
        description="Check Python environment and package installation",
    )
    diagnose_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed diagnostic information",
    )

    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest documents",
        description=(
            "Ingest .txt, .md, or .markdown files into TraceVault. "
            "Supports single files or directories."
        ),
    )
    ingest_parser.add_argument(
        "path",
        type=str,
        help="Path to file or directory to ingest",
    )
    ingest_parser.add_argument(
        "--manifest-path",
        type=str,
        default=DEFAULT_MANIFEST_PATH,
        help=f"Path to manifest file (default: {DEFAULT_MANIFEST_PATH})",
    )
    ingest_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    # Wiki-health command
    wiki_health_parser = subparsers.add_parser(
        "wiki-health",
        help="Check wiki note health",
        description=(
            "Run deterministic health/lint checks on exported "
            "wiki Markdown notes."
        ),
    )
    wiki_health_parser.add_argument(
        "path",
        type=str,
        help="Path to wiki note file or directory",
    )
    wiki_health_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    wiki_health_parser.add_argument(
        "--source-manifest",
        type=str,
        default=None,
        help="Optional path to source manifest for drift detection",
    )
    wiki_health_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on warnings as well as errors",
    )

    return parser


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command."""
    if args.brief:
        print(__version__)
    else:
        print(f"TraceVault {__version__}")
        print("  Description: Traceable Enterprise Knowledge Reasoning System")
        print("  Milestone: Foundation (documentation-to-code)")
        print(f"  Python: {sys.version}")
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Handle diagnose command."""
    print("TraceVault Diagnostic Report")
    print("=" * 40)
    print(f"Version: {__version__}")
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Platform: {sys.platform}")

    # Check package location
    package_path = Path(__file__).parent.parent
    print(f"Package location: {package_path.absolute()}")

    # Check for required directories
    required_dirs = ["cli", "config", "ingestion", "storage", "retrieval", "reasoning", "validation"]
    missing = [d for d in required_dirs if not (package_path / d).exists()]
    if missing:
        print(f"\nWarning: Missing directories: {missing}")
        return 1

    print("\nPackage structure: OK")
    print(f"Required modules present: {', '.join(required_dirs)}")

    if args.verbose:
        print("\nDetailed module check:")
        for module in required_dirs:
            module_path = package_path / module
            init_file = module_path / "__init__.py"
            status = "✓" if init_file.exists() else "✗"
            print(f"  {status} {module}")

    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Handle ingest command."""
    path = Path(args.path)

    if not path.exists():
        if args.json:
            output = {"error": f"Path not found: {args.path}", "success": False}
            print(json.dumps(output, indent=2))
        else:
            print(f"Error: Path not found: {args.path}", file=sys.stderr)
        return 1

    try:
        result = ingest_path(path, manifest_path=args.manifest_path)

        if args.json:
            if hasattr(result, "to_dict"):
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(json.dumps({
                    "source_path": result.source_path,
                    "status": result.status,
                    "document_id": result.document_record.document_id if result.document_record else None,
                    "content_hash": result.document_record.content_hash if result.document_record else None,
                    "error": result.error,
                }, indent=2))
        else:
            # Human-readable output
            if hasattr(result, "new_count"):  # Directory result
                summary = result
                print("Ingestion Summary:")
                print(f"  Total files: {summary.total_files}")
                print(f"  New: {summary.new_count}")
                print(f"  Unchanged: {summary.unchanged_count}")
                print(f"  Changed: {summary.changed_count}")
                print(f"  Skipped: {summary.skipped_count}")
                print(f"  Errors: {summary.error_count}")
                if summary.error_count > 0:
                    print("\nErrors:")
                    for r in result.results:
                        if r.status == "error":
                            print(f"  - {r.source_path}: {r.error}")
            else:  # Single file result
                r = result
                print(f"File: {r.source_path}")
                print(f"Status: {r.status}")
                if r.document_record:
                    print(f"Document ID: {r.document_record.document_id}")
                    print(f"Content Hash: {r.document_record.content_hash}")
                    print(f"Size: {r.document_record.size_bytes} bytes")
                if r.error:
                    print(f"Error: {r.error}")

        # Exit 1 if any errors occurred
        if hasattr(result, "error_count"):
            return 1 if result.error_count > 0 else 0
        return 1 if result.status == "error" else 0

    except ManifestCorruptionError as e:
        if args.json:
            print(json.dumps({"error": f"Manifest corruption: {e}", "success": False}, indent=2))
        else:
            print(f"Error: Manifest corruption detected: {e}", file=sys.stderr)
            print(f"Manifest path: {args.manifest_path}", file=sys.stderr)
            print("Please fix or remove the corrupted manifest file.", file=sys.stderr)
        return 1
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"Error during ingestion: {e}", file=sys.stderr)
        return 1


def cmd_wiki_health(args: argparse.Namespace) -> int:
    """Handle wiki-health command."""
    from tracevault.wiki.health import check_wiki_health, print_health_report

    path = Path(args.path)

    if not path.exists():
        output = {"error": f"Path not found: {args.path}", "passed": False}
        print(json.dumps(output, indent=2) if args.json else f"Error: Path not found: {args.path}")
        return 1

    # Load optional source manifest for drift detection
    source_hashes: dict[str, str] | None = None
    manifest_issues: list = []
    if args.source_manifest:
        manifest_path = Path(args.source_manifest)
        if not manifest_path.exists():
            output = {"error": f"Source manifest not found: {args.source_manifest}", "passed": False}
            print(json.dumps(output, indent=2) if args.json else (
                f"Error: Source manifest not found: {args.source_manifest}"
            ))
            return 1
        try:
            raw = manifest_path.read_text(encoding="utf-8")
            manifest_data = json.loads(raw)

            # Support real TraceVault ingestion manifest schema (entries[])
            entries = manifest_data.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    spath = entry.get("source_path")
                    chash = entry.get("content_hash")
                    if spath and chash:
                        source_hashes = source_hashes or {}
                        source_hashes[spath] = chash
            # Support simple document schema (documents[])
            elif isinstance(manifest_data.get("documents"), list):
                for entry in manifest_data.get("documents", []):
                    did = entry.get("document_id")
                    chash = entry.get("content_hash")
                    if did and chash:
                        source_hashes = source_hashes or {}
                        source_hashes[did] = chash
            else:
                # Unrecognized shape — record as structured issue
                from tracevault.wiki.report import IssueSeverity, WikiLintIssue
                manifest_issues.append(WikiLintIssue(
                    code="source_manifest_unrecognized",
                    severity=IssueSeverity.ERROR,
                    message=(
                        "Source manifest has unrecognized schema "
                        "(missing 'entries' or 'documents' list)"
                    ),
                    file_path=str(manifest_path),
                ))
                source_hashes = {}
        except json.JSONDecodeError as exc:
            output = {"error": f"Failed to parse source manifest: {exc}", "passed": False}
            print(json.dumps(output, indent=2) if args.json else (
                f"Error: Failed to parse source manifest: {exc}"
            ))
            return 1

    report = check_wiki_health(path, source_hashes=source_hashes)
    # Merge manifest-level issues into the report before printing
    report.issues.extend(manifest_issues)
    report.issues.sort(key=lambda i: (i.file_path, i.code, i.message))
    exit_code = print_health_report(report, as_json=args.json)

    # In strict mode, warnings also trigger exit 1
    if args.strict and exit_code == 0 and report.warning_count > 0:
        exit_code = 1

    return exit_code


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "version":
        return cmd_version(args)
    elif args.command == "diagnose":
        return cmd_diagnose(args)
    elif args.command == "ingest":
        return cmd_ingest(args)
    elif args.command == "wiki-health":
        return cmd_wiki_health(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
