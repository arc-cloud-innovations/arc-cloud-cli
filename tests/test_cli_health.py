"""Integration tests for ARC CLOUD platform CLI commands."""
from pathlib import Path
import tempfile
import pytest
from typer.testing import CliRunner

from arc_cloud.main import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ARC CLOUD" in result.stdout
    assert "CLI Version:" in result.stdout
    assert "Engineering Health Engines" in result.stdout


def test_cli_explain_list() -> None:
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 0
    assert "ARC001" in result.stdout
    assert "Excessive Function Complexity" in result.stdout


def test_cli_explain_single_rule() -> None:
    result = runner.invoke(app, ["explain", "ARC001"])
    assert result.exit_code == 0
    assert "ARC001" in result.stdout
    assert "Excessive Function Complexity" in result.stdout
    assert "Why It Matters" in result.stdout


def test_cli_explain_unknown_rule() -> None:
    result = runner.invoke(app, ["explain", "ARC999"])
    assert result.exit_code == 2
    assert "Unknown rule ID 'ARC999'" in result.stderr or "Unknown rule ID 'ARC999'" in result.stdout


def test_cli_init_command() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["init", tmpdir])
        assert result.exit_code == 0
        cfg_path = Path(tmpdir) / ".arccloud.yml"
        assert cfg_path.exists()
        content = cfg_path.read_text()
        assert "project:" in content
        assert "rules:" in content
        assert "ARC001" in content


def test_cli_scan_clean_project() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "simple.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        result = runner.invoke(app, ["scan", tmpdir])
        assert result.exit_code == 0
        assert "Overall Health:" in result.stdout
        assert "100/100" in result.stdout
        assert "Risk Level:" in result.stdout


def test_cli_scan_json_output() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "simple.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        result = runner.invoke(app, ["scan", tmpdir, "--format", "json"])
        assert result.exit_code == 0
        assert '"overall_score": 100.0' in result.stdout


def test_cli_scan_sarif_output() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "simple.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        result = runner.invoke(app, ["scan", tmpdir, "--format", "sarif"])
        assert result.exit_code == 0
        assert '"$schema"' in result.stdout
        assert '"version": "2.1.0"' in result.stdout


def test_cli_scan_fails_on_high_severity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        # Function with complexity >= 15 triggers HIGH severity finding
        lines = ["def complex_fn(x):"]
        for i in range(16):
            lines.append(f"    if x == {i}: pass")
        lines.append("    return x")
        (p / "complex.py").write_text("\n".join(lines), encoding="utf-8")

        # --fail-on high should trigger exit code 1
        result = runner.invoke(app, ["scan", tmpdir, "--fail-on", "high"])
        assert result.exit_code == 1
        assert "ARC001" in result.stdout


def test_cli_report_command() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "simple.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        result = runner.invoke(app, ["report", tmpdir, "--format", "json"])
        assert result.exit_code == 0
        assert '"overall_score": 100.0' in result.stdout


def test_cli_report_to_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "simple.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
        out_file = p / "health_report.json"

        result = runner.invoke(app, ["report", tmpdir, "--format", "json", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "overall_score" in out_file.read_text()
