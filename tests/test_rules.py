"""Tests for ARC CLOUD rule engine and ARC001."""
from pathlib import Path
import pytest

from arc_cloud.core.config import ArcConfig, CodeQualityConfig
from arc_cloud.core.models import FindingCategory, FindingSeverity
from arc_cloud.parsers.python_parser import PythonParser
from arc_cloud.rules.base import RuleContext
from arc_cloud.rules.code_quality.complexity import ARC001ExcessiveComplexityRule
from arc_cloud.rules.registry import RuleRegistry


def test_rule_registry() -> None:
    registry = RuleRegistry()
    rule = registry.get("ARC001")
    assert rule is not None
    assert rule.rule_id == "ARC001"
    assert rule.category == FindingCategory.CODE_QUALITY

    # Case insensitivity
    assert registry.get("arc001") is not None

    # Unknown rule returns None
    assert registry.get("ARC999") is None


def test_arc001_detects_excessive_complexity() -> None:
    code = """
def very_complex_function(x):
    if x == 1: pass
    elif x == 2: pass
    elif x == 3: pass
    elif x == 4: pass
    elif x == 5: pass
    elif x == 6: pass
    elif x == 7: pass
    elif x == 8: pass
    elif x == 9: pass
    elif x == 10: pass
    elif x == 11: pass
    return x
"""
    parser = PythonParser()
    module = parser.parse_source(code, Path("sample.py"))

    rule = ARC001ExcessiveComplexityRule()
    context = RuleContext(
        project_root=Path("."),
        file_path=Path("sample.py"),
        relative_path="sample.py",
        parsed_module=module,
        config=ArcConfig(code_quality=CodeQualityConfig(max_complexity=10)),
        file_content=code,
    )

    findings = rule.evaluate(context)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "ARC001"
    assert f.category == FindingCategory.CODE_QUALITY
    assert "cyclomatic complexity of 12" in f.description
    assert f.line == 2


def test_arc001_ignores_simple_functions() -> None:
    code = """
def simple_function(x):
    if x > 0:
        return x
    return -x
"""
    parser = PythonParser()
    module = parser.parse_source(code, Path("sample.py"))

    rule = ARC001ExcessiveComplexityRule()
    context = RuleContext(
        project_root=Path("."),
        file_path=Path("sample.py"),
        relative_path="sample.py",
        parsed_module=module,
        config=ArcConfig(code_quality=CodeQualityConfig(max_complexity=10)),
        file_content=code,
    )

    findings = rule.evaluate(context)
    assert len(findings) == 0
