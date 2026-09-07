"""CLI commands for ARC CLOUD."""
from arc_cloud.commands.init import init_command
from arc_cloud.commands.scan import scan_command
from arc_cloud.commands.explain import explain_command
from arc_cloud.commands.report import report_command
from arc_cloud.commands.version import version_command
from arc_cloud.commands.ci import ci_command
from arc_cloud.commands.engine_commands import (
    reliability_command,
    security_command,
    secrets_command,
    deps_command,
    architecture_command,
    debt_command,
    test_command,
    performance_command,
    ai_risk_command,
)
from arc_cloud.commands.ai_commands import (
    fix_command,
    plan_command,
    review_command,
    verify_command,
)

__all__ = [
    "init_command",
    "scan_command",
    "explain_command",
    "report_command",
    "version_command",
    "ci_command",
    "reliability_command",
    "security_command",
    "secrets_command",
    "deps_command",
    "architecture_command",
    "debt_command",
    "test_command",
    "performance_command",
    "ai_risk_command",
    "fix_command",
    "plan_command",
    "review_command",
    "verify_command",
]
