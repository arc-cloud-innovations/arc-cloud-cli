"""Tests for AI-assisted commands and engine subcommands."""
from pathlib import Path
import tempfile
import pytest
from typer.testing import CliRunner

from arc_cloud.main import app
from arc_cloud.verification.verifier import BaselineVerifier

runner = CliRunner()


def test_explain_with_rule_id() -> None:
    result = runner.invoke(app, ["explain", "ARC-SEC-002"])
    assert result.exit_code == 0
    assert "ARC-SEC-002" in result.stdout
    assert "SQL Injection Risk" in result.stdout
    assert "Root Cause Explanation" in result.stdout


def test_plan_command() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "service.py").write_text("def work(): pass\n", encoding="utf-8")

        result = runner.invoke(app, ["plan", tmpdir])
        assert result.exit_code == 0
        assert "Remediation Plan" in result.stdout
        assert "Overall Health Score" in result.stdout


def test_verify_command_baseline_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "code.py").write_text("def work(): pass\n", encoding="utf-8")

        # Initial verify creates baseline
        res1 = runner.invoke(app, ["verify", tmpdir])
        assert res1.exit_code == 0
        assert "Initial baseline created" in res1.stdout
        assert (p / ".arc" / "baseline.json").is_file()

        # Second verify reports trend
        res2 = runner.invoke(app, ["verify", tmpdir])
        assert res2.exit_code == 0
        assert "UNCHANGED" in res2.stdout or "Verification Delta" in res2.stdout


def test_engine_subcommands() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "mod.py").write_text("def f(): return 1\n", encoding="utf-8")

        for cmd in [
            "reliability",
            "security",
            "secrets",
            "deps",
            "architecture",
            "debt",
            "test",
            "performance",
            "ai-risk",
        ]:
            res = runner.invoke(app, [cmd, tmpdir])
            assert res.exit_code == 0
            assert "Engine" in res.stdout
