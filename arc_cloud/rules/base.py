"""Base classes for the ARC CLOUD Rule Engine."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import Finding, FindingCategory, FindingSeverity, ProjectProfile
from arc_cloud.parsers.base import ParsedModule


@dataclass
class RuleContext:
    """Context provided to rules during evaluation."""
    project_root: Path
    file_path: Path
    relative_path: str
    parsed_module: Optional[ParsedModule] = None
    profile: Optional[ProjectProfile] = None
    config: Optional[ArcConfig] = None
    file_content: Optional[str] = None


class BaseRule(ABC):
    """Abstract base class for all ARC CLOUD rules."""

    rule_id: str
    title: str
    category: FindingCategory
    default_severity: FindingSeverity
    description: str
    recommendation: str
    why_it_matters: str = ""
    example_bad: str = ""
    example_good: str = ""

    @abstractmethod
    def evaluate(self, context: RuleContext) -> List[Finding]:
        """Evaluates the context and returns any findings."""
        pass
