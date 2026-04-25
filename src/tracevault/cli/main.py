"""TraceVault CLI - Traceable Enterprise Knowledge Reasoning System.

Usage:
    python -m tracevault --help
    python -m tracevault version
    python -m tracevault diagnose
"""

import argparse
import sys
from pathlib import Path

from tracevault import __version__


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
            "Phase 1: Foundation (documentation-to-code setup)"
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

    return parser


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command."""
    if args.brief:
        print(__version__)
    else:
        print(f"TraceVault {__version__}")
        print(f"  Description: Traceable Enterprise Knowledge Reasoning System")
        print(f"  Phase: 1 (Foundation)")
        print(f"  Python: {sys.version}")
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Handle diagnose command."""
    print(f"TraceVault Diagnostic Report")
    print(f"=" * 40)
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

    print(f"\nPackage structure: OK")
    print(f"Required modules present: {', '.join(required_dirs)}")

    if args.verbose:
        print(f"\nDetailed module check:")
        for module in required_dirs:
            module_path = package_path / module
            init_file = module_path / "__init__.py"
            status = "✓" if init_file.exists() else "✗"
            print(f"  {status} {module}")

    return 0


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
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
