from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import EngineStatus, Finding, FindingCategory, ProjectProfile


@dataclass
class EngineResult:
    """Result returned by an analysis engine."""
    engine_name: str
    status: EngineStatus = EngineStatus.ANALYZED
    score: Optional[int] = None
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    message: Optional[str] = None


class BaseEngine(ABC):
    """Abstract interface for ARC CLOUD specialized engines."""

    name: str
    version: str = "1.0.0"
    category: FindingCategory

    @abstractmethod
    def is_available(self) -> bool:
        """Indicates whether this engine is enabled and ready to run."""
        pass

    @abstractmethod
    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        """Executes engine analysis against the project."""
        pass
