"""Central scan orchestrator coordinating profiling, engines, scoring, and reports."""
from pathlib import Path
from typing import List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import Finding, FindingSeverity, HealthReport
from arc_cloud.engines.code_quality import CodeQualityEngine
from arc_cloud.project.profile import ProjectProfileBuilder
from arc_cloud.scoring.health import HealthEngine
from arc_cloud.scoring.risk import RiskEngine


class ScanOrchestrator:
    """Coordinates static analysis workflow for a project."""

    def __init__(self, config: Optional[ArcConfig] = None) -> None:
        self.config = config
        self.code_quality_engine = CodeQualityEngine()

    def run_scan(self, project_root: Path) -> HealthReport:
        """Executes a full engineering health scan on the target project directory."""
        # 1. Resolve configuration
        config = self.config or ArcConfig.load(project_root)

        # 2. Build project profile (indexing + language/framework detection)
        exclude_dirs = config.scan.exclude if config and config.scan else None
        max_files = config.scan.max_files if config and config.scan else 20_000
        max_depth = config.scan.max_depth if config and config.scan else 20
        project_name = config.project_name if config else None

        profile = ProjectProfileBuilder.build(
            root_dir=project_root,
            project_name=project_name,
            exclude_dirs=exclude_dirs,
            max_files=max_files,
            max_depth=max_depth,
        )

        # 3. Execute active engines
        findings: List[Finding] = []
        if self.code_quality_engine.is_available():
            cq_result = self.code_quality_engine.analyze(project_root, profile, config)
            findings.extend(cq_result.findings)

        # 4. Compute risk assessment
        risk_assessment = RiskEngine.assess(findings)

        # 5. Compute health score
        health_score = HealthEngine.calculate(findings, profile)

        # 6. Generate actionable next steps
        actions = self._generate_actions(findings)

        return HealthReport(
            project_profile=profile,
            health_score=health_score,
            risk_assessment=risk_assessment,
            findings=findings,
            actions=actions,
        )

    def _generate_actions(self, findings: List[Finding]) -> List[str]:
        actions: List[str] = []
        if not findings:
            actions.append("Keep up the great work! No active quality issues detected.")
            return actions

        # Count high and critical issues
        crit_count = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        med_count = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)

        if crit_count > 0:
            actions.append(f"Address {crit_count} Critical-severity issue(s) immediately before shipping.")
        if high_count > 0:
            actions.append(f"Refactor {high_count} High-severity function complexity issue(s).")
        if med_count > 0 and crit_count == 0 and high_count == 0:
            actions.append(f"Review {med_count} Medium-severity complexity issue(s) during your next sprint.")

        rule_ids = sorted(list({f.rule_id for f in findings}))
        for rid in rule_ids:
            actions.append(f"Run 'arc explain {rid}' for remediation guidance.")

        return actions
