"""CLI tests for TraceVault.

Tests CLI commands using subprocess to verify exit codes and output.
"""

import subprocess
import sys


class TestCLI:
    """Test CLI commands."""

    def test_help_exits_zero(self):
        """Test --help exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "TraceVault" in result.stdout

    def test_version_flag_exits_zero(self):
        """Test --version exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "TraceVault" in result.stdout

    def test_version_command_exits_zero(self):
        """Test version command exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "TraceVault" in result.stdout
        assert "Description" in result.stdout

    def test_diagnose_command_exits_zero(self):
        """Test diagnose command exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "diagnose"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "TraceVault Diagnostic Report" in result.stdout
        assert "Package structure: OK" in result.stdout

    def test_diagnose_verbose_exits_zero(self):
        """Test diagnose --verbose exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "diagnose", "--verbose"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Detailed module check" in result.stdout

    def test_no_args_shows_help(self):
        """Test no args shows help and exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout

    def test_version_shows_milestone_not_phase(self):
        """Test version output uses milestone terminology."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should say "Milestone" not "Phase: 1"
        assert "Milestone" in result.stdout
        assert "Phase: 1" not in result.stdout

    def test_help_shows_milestone_not_phase(self):
        """Test help epilog uses milestone terminology."""
        result = subprocess.run(
            [sys.executable, "-m", "tracevault", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should say "Foundation milestone" not "Phase 1"
        # Note: epilog may wrap across lines, so check individually
        assert "Foundation" in result.stdout
        assert "milestone" in result.stdout
        assert "Phase 1" not in result.stdout
