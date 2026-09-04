"""Pydantic data models for ARC CLOUD Software Blueprint schema v1.0."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    MOBILE = "Mobile Application"
    WEB = "Web Application"
    BACKEND = "Backend"
    FULL_STACK = "Full Stack"
    DESKTOP = "Desktop Application"
    LIBRARY = "Library"
    CLI = "CLI Application"
    UNKNOWN = "Unknown"


class PlatformType(str, Enum):
    ANDROID = "Android"
    IOS = "iOS"
    WEB = "Web"
    WINDOWS = "Windows"
    MACOS = "macOS"
    LINUX = "Linux"


class ProjectInfo(BaseModel):
    name: str = Field(description="Name of the analyzed project")
    type: ProjectType = Field(default=ProjectType.UNKNOWN, description="Classified project type")
    root_path: Optional[str] = Field(default=None, description="Absolute or relative root path of the project")
    description: Optional[str] = Field(default=None, description="Optional project description from manifest")


class LanguageMetric(BaseModel):
    name: str = Field(description="Programming language name")
    files: int = Field(ge=0, description="Total number of files identified for this language")
    percentage: float = Field(ge=0.0, le=100.0, description="Percentage of total code files")


class FrameworkMetric(BaseModel):
    name: str = Field(description="Framework name (e.g. Flutter, React, FastAPI)")
    version: Optional[str] = Field(default=None, description="Detected framework version, if available")
    category: Optional[str] = Field(default=None, description="Frontend, Backend, Mobile, Fullstack, etc.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")


class PlatformInfo(BaseModel):
    name: PlatformType = Field(description="Target platform name")
    source: Optional[str] = Field(default=None, description="Directory or configuration that confirmed the platform")


class DependencyInfo(BaseModel):
    name: str = Field(description="Dependency package name")
    version: Optional[str] = Field(default=None, description="Version specifier or pinned version")
    source: str = Field(description="Manifest file source (e.g. package.json, requirements.txt)")
    type: Optional[str] = Field(default="runtime", description="Dependency type: runtime, dev, peer, test")


class ConfigFileInfo(BaseModel):
    path: str = Field(description="Relative path to configuration file")
    name: str = Field(description="Filename of the configuration")
    type: str = Field(description="Category of config, e.g. package, docker, build, git, documentation")


class StructureArea(BaseModel):
    name: str = Field(description="Functional area, e.g. source, tests, assets, platform, docs, config")
    paths: List[str] = Field(default_factory=list, description="Relative paths belonging to this area")


class StructureInfo(BaseModel):
    areas: List[StructureArea] = Field(default_factory=list, description="Classified functional directory areas")
    total_files: int = Field(default=0, ge=0, description="Total scanned files considered")
    total_directories: int = Field(default=0, ge=0, description="Total directories visited")
    ignored_directories: List[str] = Field(default_factory=list, description="Ignored directory names detected")


class ArchitectureSummary(BaseModel):
    patterns: List[str] = Field(default_factory=list, description="Detected architectural patterns or indicators")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structural indicators and metadata")


class ScannerMetadata(BaseModel):
    name: str = Field(default="ARC CLOUD CLI", description="Name of the scanner engine")
    version: str = Field(default="0.1.0", description="Scanner CLI version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Scan completion timestamp in UTC"
    )
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Total scan execution duration in seconds")
    files_scanned: int = Field(default=0, ge=0, description="Count of files analyzed")


class Blueprint(BaseModel):
    schema_version: str = Field(default="1.0", description="Software Blueprint schema version")
    scanner: ScannerMetadata = Field(default_factory=ScannerMetadata)
    project: ProjectInfo
    languages: List[LanguageMetric] = Field(default_factory=list)
    frameworks: List[FrameworkMetric] = Field(default_factory=list)
    platforms: List[PlatformInfo] = Field(default_factory=list)
    dependencies: List[DependencyInfo] = Field(default_factory=list)
    configuration_files: List[ConfigFileInfo] = Field(default_factory=list)
    structure: StructureInfo = Field(default_factory=StructureInfo)
    architecture: ArchitectureSummary = Field(default_factory=ArchitectureSummary)
    warnings: List[str] = Field(default_factory=list)
