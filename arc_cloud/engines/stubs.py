"""Future engine interfaces for ARC CLOUD platform extensions."""
from pathlib import Path
from typing import Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import FindingCategory, ProjectProfile
from arc_cloud.engines.base import BaseEngine, EngineResult


class SecurityEngine(BaseEngine):
    """Placeholder for future ARC Security engine (SAST, secrets, CVEs)."""
    name = "security"
    version = "0.1.0"
    category = FindingCategory.SECURITY

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="Security engine is scheduled for ARC CLOUD v0.2.0.",
        )


class DependencyEngine(BaseEngine):
    """Placeholder for future ARC Dependency engine (vulnerability & license auditing)."""
    name = "dependency"
    version = "0.1.0"
    category = FindingCategory.DEPENDENCY

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="Dependency engine is scheduled for ARC CLOUD v0.2.0.",
        )


class ArchitectureEngine(BaseEngine):
    """Placeholder for future ARC Architecture engine (layer violations, coupling)."""
    name = "architecture"
    version = "0.1.0"
    category = FindingCategory.ARCHITECTURE

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="Architecture engine is scheduled for ARC CLOUD v0.3.0.",
        )


class TechnicalDebtEngine(BaseEngine):
    """Placeholder for future ARC Technical Debt engine (hotspots, churn, rework)."""
    name = "technical_debt"
    version = "0.1.0"
    category = FindingCategory.TECHNICAL_DEBT

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="Technical Debt engine is scheduled for ARC CLOUD v0.3.0.",
        )


class AIEngine(BaseEngine):
    """Placeholder for future local/enterprise AI code intelligence engine."""
    name = "ai_engine"
    version = "0.1.0"
    category = FindingCategory.CODE_QUALITY

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="AI Engine interface is defined for optional enterprise extensions.",
        )


class VerificationEngine(BaseEngine):
    """Placeholder for future fix verification and regression testing engine."""
    name = "verification"
    version = "0.1.0"
    category = FindingCategory.CODE_QUALITY

    def is_available(self) -> bool:
        return False

    def analyze(self, project_root: Path, profile: ProjectProfile, config: Optional[ArcConfig] = None) -> EngineResult:
        return EngineResult(
            engine_name=self.name,
            status="not_implemented",
            message="Verification engine is defined for future automated verification workflows.",
        )
