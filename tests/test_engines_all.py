"""Tests covering all 10 specialized engineering health engines."""
from pathlib import Path
import tempfile
import pytest

from arc_cloud.core.models import EngineStatus, FindingSeverity
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.engines import (
    CodeQualityEngine,
    ReliabilityEngine,
    SecurityEngine,
    SecretsEngine,
    DependencyEngine,
    ArchitectureEngine,
    TechnicalDebtEngine,
    TestingEngine,
    PerformanceEngine,
    AIRiskEngine,
)
from arc_cloud.project.profile import ProjectProfileBuilder


def test_all_10_engines_instantiation() -> None:
    engines = [
        CodeQualityEngine(),
        ReliabilityEngine(),
        SecurityEngine(),
        SecretsEngine(),
        DependencyEngine(),
        ArchitectureEngine(),
        TechnicalDebtEngine(),
        TestingEngine(),
        PerformanceEngine(),
        AIRiskEngine(),
    ]
    assert len(engines) == 10
    names = {e.name for e in engines}
    expected = {
        "code_quality",
        "reliability",
        "security",
        "secrets",
        "dependencies",
        "architecture",
        "technical_debt",
        "testing",
        "performance",
        "ai_risk",
    }
    assert names == expected


def test_reliability_engine_catches_broad_exception_and_unclosed_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "bad_code.py").write_text(
            """
def leak():
    f = open('data.txt', 'r')
    try:
        do_work()
    except Exception:
        pass
""",
            encoding="utf-8",
        )
        profile = ProjectProfileBuilder.build(p)
        engine = ReliabilityEngine()
        result = engine.analyze(p, profile)
        assert result.status == EngineStatus.ANALYZED
        assert len(result.findings) >= 2
        rule_ids = {f.rule_id for f in result.findings}
        assert "ARC-REL-001" in rule_ids
        assert "ARC-REL-002" in rule_ids


def test_security_engine_catches_injections_and_insecure_http() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "vuln.py").write_text(
            """
import subprocess
import hashlib

def run_query(user_id):
    sql = f"SELECT * FROM users WHERE id = '{user_id}'"
    eval("2 + 2")
    subprocess.run("ls " + user_id, shell=True)
    h = hashlib.md5(b"test").hexdigest()
    url = "http://api.insecure.com/auth"
""",
            encoding="utf-8",
        )
        profile = ProjectProfileBuilder.build(p)
        engine = SecurityEngine()
        result = engine.analyze(p, profile)
        assert result.status == EngineStatus.ANALYZED
        rule_ids = {f.rule_id for f in result.findings}
        assert "ARC-SEC-002" in rule_ids
        assert "ARC-SEC-003" in rule_ids
        assert "ARC-SEC-005" in rule_ids
        assert "ARC-SEC-007" in rule_ids
        assert "ARC-SEC-008" in rule_ids


def test_secrets_engine_masks_credentials() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "config.py").write_text(
            """
AWS_KEY = "AKIA1234567890ABCDEF"
GITHUB_TOKEN = "ghp_123456789012345678901234567890123456"
""",
            encoding="utf-8",
        )
        profile = ProjectProfileBuilder.build(p)
        engine = SecretsEngine()
        result = engine.analyze(p, profile)
        assert result.status == EngineStatus.ANALYZED
        assert len(result.findings) >= 2
        for f in result.findings:
            # Secrets MUST be masked, never raw
            assert "AKIA1234567890ABCDEF" not in f.message
            assert "ghp_123456789012345678901234567890123456" not in f.message
            assert "..." in f.message


def test_dependency_engine_flags_wildcards() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "package.json").write_text(
            """
{
  "name": "sample",
  "dependencies": {
    "lodash": "*",
    "express": "^4.18.2"
  }
}
""",
            encoding="utf-8",
        )
        profile = ProjectProfileBuilder.build(p)
        engine = DependencyEngine()
        result = engine.analyze(p, profile)
        assert result.status == EngineStatus.ANALYZED
        assert any(f.rule_id == "ARC-DEP-001" for f in result.findings)
        assert result.metrics.get("vulnerabilities") == "NOT ANALYZED (No vulnerability database configured)"


def test_performance_engine_detects_nested_loops_and_regex() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "perf.py").write_text(
            """
import re

def heavy(items):
    for i in items:
        for j in items:
            for k in items:
                re.compile(r"\\d+")
""",
            encoding="utf-8",
        )
        profile = ProjectProfileBuilder.build(p)
        engine = PerformanceEngine()
        result = engine.analyze(p, profile)
        assert result.status == EngineStatus.ANALYZED
        rule_ids = {f.rule_id for f in result.findings}
        assert "ARC-PERF-001" in rule_ids
        assert "ARC-PERF-002" in rule_ids


def test_full_orchestrator_10_engines() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "clean.py").write_text("def ping(): return 'pong'\n", encoding="utf-8")
        orchestrator = ScanOrchestrator()
        report = orchestrator.run_scan(p)

        assert report.health_score.overall_score == 100.0
        assert report.health_score.letter_grade == "A"
        assert report.health_score.analyzed_count >= 7
        assert len(report.engine_results) == 10
