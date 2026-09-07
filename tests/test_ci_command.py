"""Tests for the ARC CLOUD CI/CD command quality gates."""
from pathlib import Path
import tempfile
import pytest
from typer.testing import CliRunner

from arc_cloud.main import app

runner = CliRunner()


def test_ci_clean_project_passes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "clean.py").write_text("def ping(): return 'pong'\n", encoding="utf-8")

        result = runner.invoke(app, ["ci", tmpdir, "--fail-on", "high"])
        assert result.exit_code == 0
        assert "CI Quality Gate PASSED" in result.stdout
        assert (p / "arc-results.sarif").is_file()


def test_ci_fails_on_severity_threshold() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "vuln.py").write_text(
            """
import subprocess
def run_cmd(user_arg):
    subprocess.run("rm " + user_arg, shell=True)
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["ci", tmpdir, "--fail-on", "high"])
        assert result.exit_code == 1
        assert "CI Quality Gate FAILED" in result.stdout


def test_ci_min_health_threshold() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "app.py").write_text("def run(): pass\n", encoding="utf-8")

        # Demand 100% health -> should pass
        result = runner.invoke(app, ["ci", tmpdir, "--min-health", "90"])
        assert result.exit_code == 0
