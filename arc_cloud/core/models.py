"""Core data models for ARC CLOUD Software Engineering Health Platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FindingSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingCategory(str, Enum):
    CODE_QUALITY = "code_quality"
    RELIABILITY = "reliability"
    SECURITY = "security"
    SECRETS = "secrets"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    PERFORMANCE = "performance"
    TECHNICAL_DEBT = "technical_debt"
    AI_CODE_RISK = "ai_code_risk"


class EngineStatus(str, Enum):
    ANALYZED = "ANALYZED"
    NOT_ANALYZED = "NOT_ANALYZED"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class Finding(BaseModel):
    """Unified finding contract produced by all ARC CLOUD rules and engines."""
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique finding identifier")
    rule_id: str = Field(description="Rule identifier, e.g. ARC001 or ARC-SEC-001")
    engine: str = Field(default="code_quality", description="Originating engine name")
    category: FindingCategory = Field(description="Finding category")
    severity: FindingSeverity = Field(description="Centralized severity level")
    title: str = Field(description="Short human-readable finding title")
    message: str = Field(default="", description="Detailed finding explanation")
    file: str = Field(default="", description="Relative path to file containing issue")
    line: int = Field(default=1, ge=1, description="1-indexed line number")
    column: Optional[int] = Field(default=1, ge=0, description="Column number")
    end_line: Optional[int] = Field(default=None, description="Ending line number")
    end_col: Optional[int] = Field(default=None, description="Ending column number")
    evidence: Optional[str] = Field(default=None, description="Code snippet or metric evidence")
    recommendation: str = Field(default="", description="Actionable fix advice")
    language: Optional[str] = Field(default=None, description="Programming language associated with finding")
    framework: Optional[str] = Field(default=None, description="Framework associated with finding")
    confidence: str = Field(default="HIGH", description="Finding confidence: LOW, MEDIUM, HIGH")
    risk_score: int = Field(default=0, description="Calculated finding risk score")
    estimated_fix_minutes: int = Field(default=15, description="Estimated minutes to remediate")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific additional attributes")

    def __init__(
        self,
        id: Optional[str] = None,
        description: Optional[str] = None,
        file_path: Optional[str] = None,
        col: Optional[int] = None,
        code_snippet: Optional[str] = None,
        **data: Any,
    ) -> None:
        if id and "finding_id" not in data:
            data["finding_id"] = id
        if description and "message" not in data:
            data["message"] = description
        if file_path and "file" not in data:
            data["file"] = file_path
        if col is not None and "column" not in data:
            data["column"] = col
        if code_snippet and "evidence" not in data:
            data["evidence"] = code_snippet
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.finding_id

    @property
    def description(self) -> str:
        return self.message

    @property
    def file_path(self) -> str:
        return self.file

    @property
    def col(self) -> Optional[int]:
        return self.column

    @property
    def code_snippet(self) -> Optional[str]:
        return self.evidence


class ProjectProfile(BaseModel):
    """Normalized project profile describing intelligence, files, and ecosystem."""
    project_name: str
    name: Optional[str] = None
    root_path: str
    languages: Any = Field(default_factory=list)
    primary_language: Optional[str] = None
    frameworks: Any = Field(default_factory=list)
    package_managers: List[str] = Field(default_factory=list)
    build_systems: List[str] = Field(default_factory=list)
    project_type: str = "Unknown"
    source_files: List[str] = Field(default_factory=list)
    test_files: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    dependency_files: List[str] = Field(default_factory=list)
    file_count: int = Field(default=0, ge=0)
    line_count: int = Field(default=0, ge=0)
    source_line_count: int = Field(default=0, ge=0)
    test_line_count: int = Field(default=0, ge=0)
    project_tree: Dict[str, List[str]] = Field(default_factory=dict)

    def __init__(
        self,
        name: Optional[str] = None,
        total_files: Optional[int] = None,
        total_loc: Optional[int] = None,
        source_loc: Optional[int] = None,
        test_loc: Optional[int] = None,
        **data: Any,
    ) -> None:
        if name and "project_name" not in data:
            data["project_name"] = name
        if "project_name" in data and "name" not in data:
            data["name"] = data["project_name"]
        elif name and "name" not in data:
            data["name"] = name
        if total_files is not None and "file_count" not in data:
            data["file_count"] = total_files
        if total_loc is not None and "line_count" not in data:
            data["line_count"] = total_loc
        if source_loc is not None and "source_line_count" not in data:
            data["source_line_count"] = source_loc
        if test_loc is not None and "test_line_count" not in data:
            data["test_line_count"] = test_loc
        super().__init__(**data)

    @property
    def total_files(self) -> int:
        return self.file_count

    @property
    def total_loc(self) -> int:
        return self.line_count

    @property
    def total_lines(self) -> int:
        return self.line_count

    @property
    def source_loc(self) -> int:
        return self.source_line_count

    @property
    def test_loc(self) -> int:
        return self.test_line_count

    @property
    def architecture_type(self) -> str:
        return self.project_type or "Unknown"

    @property
    def architecture(self) -> str:
        return self.project_type or "Unknown"


class HealthScore(BaseModel):
    """Software health score and multidimensional ratings across all 10 engines."""
    overall_health: int = Field(default=100, ge=0, le=100, description="Overall health score (0-100)")
    code_quality: Optional[int] = Field(default=None, ge=0, le=100)
    reliability: Optional[int] = Field(default=None, ge=0, le=100)
    security: Optional[int] = Field(default=None, ge=0, le=100)
    dependencies: Optional[int] = Field(default=None, ge=0, le=100)
    secrets: Optional[int] = Field(default=None, ge=0, le=100)
    architecture: Optional[int] = Field(default=None, ge=0, le=100)
    technical_debt: Optional[int] = Field(default=None, ge=0, le=100)
    testing: Optional[int] = Field(default=None, ge=0, le=100)
    performance: Optional[int] = Field(default=None, ge=0, le=100)
    ai_risk: Optional[str] = Field(default=None, description="AI Code Risk rating (LOW, MEDIUM, HIGH)")
    engine_statuses: Dict[str, str] = Field(default_factory=dict)
    analysis_coverage: str = Field(default="1/10 engines analyzed")
    analyzed_count: int = Field(default=1)
    total_engines_count: int = Field(default=10)
    grade: str = Field(default="A", description="Letter grade (A-F)")
    explanation: str = Field(default="", description="Explanation of calculation")
    status_dimensions: Dict[str, str] = Field(default_factory=dict)

    def __init__(
        self,
        overall_score: Optional[float] = None,
        code_quality_score: Optional[float] = None,
        reliability_score: Optional[float] = None,
        security_score: Optional[float] = None,
        dependency_score: Optional[float] = None,
        secrets_score: Optional[float] = None,
        architecture_score: Optional[float] = None,
        technical_debt_score: Optional[float] = None,
        testing_score: Optional[float] = None,
        performance_score: Optional[float] = None,
        **data: Any,
    ) -> None:
        if overall_score is not None and "overall_health" not in data:
            data["overall_health"] = int(round(overall_score))
        if code_quality_score is not None and "code_quality" not in data:
            data["code_quality"] = int(round(code_quality_score))
        if reliability_score is not None and "reliability" not in data:
            data["reliability"] = int(round(reliability_score))
        if security_score is not None and "security" not in data:
            data["security"] = int(round(security_score))
        if dependency_score is not None and "dependencies" not in data:
            data["dependencies"] = int(round(dependency_score))
        if secrets_score is not None and "secrets" not in data:
            data["secrets"] = int(round(secrets_score))
        if architecture_score is not None and "architecture" not in data:
            data["architecture"] = int(round(architecture_score))
        if technical_debt_score is not None and "technical_debt" not in data:
            data["technical_debt"] = int(round(technical_debt_score))
        if testing_score is not None and "testing" not in data:
            data["testing"] = int(round(testing_score))
        if performance_score is not None and "performance" not in data:
            data["performance"] = int(round(performance_score))
        super().__init__(**data)

    @property
    def overall_score(self) -> float:
        return float(self.overall_health)

    @property
    def code_quality_score(self) -> Optional[float]:
        return float(self.code_quality) if self.code_quality is not None else None

    @property
    def reliability_score(self) -> Optional[float]:
        return float(self.reliability) if self.reliability is not None else None

    @property
    def security_score(self) -> Optional[float]:
        return float(self.security) if self.security is not None else None

    @property
    def dependency_score(self) -> Optional[float]:
        return float(self.dependencies) if self.dependencies is not None else None

    @property
    def secrets_score(self) -> Optional[float]:
        return float(self.secrets) if self.secrets is not None else None

    @property
    def architecture_score(self) -> Optional[float]:
        return float(self.architecture) if self.architecture is not None else None

    @property
    def technical_debt_score(self) -> Optional[float]:
        return float(self.technical_debt) if self.technical_debt is not None else None

    @property
    def testing_score(self) -> Optional[float]:
        return float(self.testing) if self.testing is not None else None

    @property
    def performance_score(self) -> Optional[float]:
        return float(self.performance) if self.performance is not None else None

    @property
    def letter_grade(self) -> str:
        return self.grade


class RiskAssessment(BaseModel):
    """Risk engine analysis of findings."""
    total_risk_points: int = Field(default=0, ge=0, description="Sum of weighted finding points")
    risk_level: str = Field(default="NONE", description="NONE, LOW, MEDIUM, HIGH, or CRITICAL")
    severity_counts: Dict[str, int] = Field(default_factory=dict)

    def __init__(
        self,
        level: Optional[str] = None,
        total_risk_score: Optional[int] = None,
        critical_count: Optional[int] = None,
        high_count: Optional[int] = None,
        medium_count: Optional[int] = None,
        low_count: Optional[int] = None,
        info_count: Optional[int] = None,
        **data: Any,
    ) -> None:
        if level and "risk_level" not in data:
            data["risk_level"] = level
        if total_risk_score is not None and "total_risk_points" not in data:
            data["total_risk_points"] = total_risk_score
        counts = data.get("severity_counts", {})
        if critical_count is not None:
            counts["CRITICAL"] = critical_count
        if high_count is not None:
            counts["HIGH"] = high_count
        if medium_count is not None:
            counts["MEDIUM"] = medium_count
        if low_count is not None:
            counts["LOW"] = low_count
        if info_count is not None:
            counts["INFO"] = info_count
        data["severity_counts"] = counts
        super().__init__(**data)

    @property
    def level(self) -> str:
        return self.risk_level

    @property
    def total_risk_score(self) -> int:
        return self.total_risk_points

    @property
    def overall_risk_score(self) -> float:
        return float(self.total_risk_points)

    @property
    def critical_count(self) -> int:
        return self.severity_counts.get("CRITICAL", 0)

    @property
    def high_count(self) -> int:
        return self.severity_counts.get("HIGH", 0)

    @property
    def medium_count(self) -> int:
        return self.severity_counts.get("MEDIUM", 0)

    @property
    def low_count(self) -> int:
        return self.severity_counts.get("LOW", 0)

    @property
    def info_count(self) -> int:
        return self.severity_counts.get("INFO", 0)


class HealthReport(BaseModel):
    """Complete Software Health Report produced by arc scan."""
    schema_version: str = "1.0"
    scanner_name: str = "ARC CLOUD"
    scanner_version: str = "0.2.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = Field(default=0.0, ge=0.0)
    project: ProjectProfile
    health: HealthScore
    risk: RiskAssessment
    findings: List[Finding] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    engine_results: Dict[str, Any] = Field(default_factory=dict)
    technical_debt_estimate: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        project_profile: Optional[ProjectProfile] = None,
        health_score: Optional[HealthScore] = None,
        risk_assessment: Optional[RiskAssessment] = None,
        **data: Any,
    ) -> None:
        if project_profile and "project" not in data:
            data["project"] = project_profile
        if health_score and "health" not in data:
            data["health"] = health_score
        if risk_assessment and "risk" not in data:
            data["risk"] = risk_assessment
        super().__init__(**data)
        if not self.recommendations and self.actions:
            self.recommendations = list(self.actions)
        elif not self.actions and self.recommendations:
            self.actions = list(self.recommendations)

    @property
    def project_profile(self) -> ProjectProfile:
        return self.project

    @property
    def health_score(self) -> HealthScore:
        return self.health

    @property
    def risk_assessment(self) -> RiskAssessment:
        return self.risk

    @property
    def risk_profile(self) -> RiskAssessment:
        return self.risk

    @property
    def scanned_at(self) -> datetime:
        return self.timestamp
