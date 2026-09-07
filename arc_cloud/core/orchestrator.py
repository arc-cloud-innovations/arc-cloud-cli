"""Central scan orchestrator coordinating profiling, engines, scoring, and reports."""
import time
from pathlib import Path
from typing import Dict, List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    Finding,
    FindingSeverity,
    HealthReport,
)
from arc_cloud.engines.architecture import ArchitectureEngine
from arc_cloud.engines.base import BaseEngine, EngineResult
from arc_cloud.engines.code_quality import CodeQualityEngine
from arc_cloud.engines.dependencies import DependencyEngine
from arc_cloud.engines.performance import PerformanceEngine
from arc_cloud.engines.reliability import ReliabilityEngine
from arc_cloud.engines.secrets import SecretsEngine
from arc_cloud.engines.security import SecurityEngine
from arc_cloud.engines.technical_debt import TechnicalDebtEngine
from arc_cloud.engines.testing import TestingEngine
from arc_cloud.engines.ai_risk import AIRiskEngine
from arc_cloud.project.profile import ProjectProfileBuilder
from arc_cloud.scoring.health import HealthEngine
from arc_cloud.scoring.risk import RiskEngine


class ScanOrchestrator:
    """Coordinates static analysis workflow across all 10 platform engines."""

    def __init__(self, config: Optional[ArcConfig] = None) -> None:
        self.config = config
        self.engines: List[BaseEngine] = [
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

    def run_scan(self, project_root: Path, target_engine: Optional[str] = None) -> HealthReport:
        """Executes full engineering health scan or single-engine scan."""
        start_time = time.perf_counter()

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

        # 3. Execute engines
        findings: List[Finding] = []
        engine_results: Dict[str, EngineResult] = {}

        for engine in self.engines:
            if target_engine and engine.name != target_engine:
                continue

            if engine.is_available():
                try:
                    res = engine.analyze(project_root, profile, config)
                    engine_results[engine.name] = res
                    findings.extend(res.findings)
                except Exception as exc:
                    from arc_cloud.core.models import EngineStatus
                    engine_results[engine.name] = EngineResult(
                        engine_name=engine.name,
                        status=EngineStatus.ERROR,
                        message=str(exc),
                    )

        # 4. Compute Technical Debt
        debt_estimate = TechnicalDebtEngine.calculate_debt_from_findings(findings)

        # 5. Compute risk assessment
        risk_assessment = RiskEngine.assess(findings)

        # 6. Compute health score across analyzed engines
        health_score = HealthEngine.calculate(findings, profile, engine_results)

        # 7. Generate actionable recommendations
        actions = self._generate_actions(findings)

        duration = round(time.perf_counter() - start_time, 2)

        return HealthReport(
            duration_seconds=duration,
            project=profile,
            health=health_score,
            risk=risk_assessment,
            findings=findings,
            actions=actions,
            recommendations=actions,
            engine_results={k: v.__dict__ if hasattr(v, "__dict__") else v for k, v in engine_results.items()},
            technical_debt_estimate=debt_estimate,
        )

    def _generate_actions(self, findings: List[Finding]) -> List[str]:
        actions: List[str] = []
        if not findings:
            actions.append("Keep up the great work! No active quality issues detected.")
            return actions

        # Check for exposed credentials first (Highest priority)
        sec_findings = [f for f in findings if f.category == FindingSeverity.CRITICAL or "SEC" in f.rule_id]
        if sec_findings:
            actions.append("Immediately remove exposed credentials or rotate compromised keys.")

        # Check for command or SQL injection
        inj_findings = [f for f in findings if f.rule_id in ("ARC-SEC-002", "ARC-SEC-003", "ARC-SEC-005")]
        if inj_findings:
            actions.append("Remediate critical injection/eval risks in source code.")

        # Check for circular dependencies
        arch_findings = [f for f in findings if f.rule_id == "ARC-ARCH-001"]
        if arch_findings:
            actions.append("Resolve circular module dependencies to decouple packages.")

        # Check for missing critical tests
        test_findings = [f for f in findings if f.rule_id == "ARC-TEST-001"]
        if test_findings:
            actions.append("Add automated tests for critical untested services.")

        # Check for complexity
        cq_findings = [f for f in findings if f.rule_id in ("ARC001", "ARC002", "ARC003")]
        if cq_findings:
            actions.append(f"Refactor {len(cq_findings)} high-complexity and nested function(s).")

        if not actions:
            actions.append("Review findings and apply recommended remediations.")

        return actions[:5]  # Top 5 actions
