"""Framework detectors for ARC CLOUD CLI."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml

from arc_cloud.blueprint.models import DependencyInfo, FrameworkMetric
from arc_cloud.utils.security import SecurityManager


@dataclass
class ScanContext:
    """Shared immutable context provided to all framework detectors."""
    root_dir: Path
    relative_files: List[str]
    relative_dirs: List[str]
    dependencies: List[DependencyInfo]
    files_set: Set[str]
    security: SecurityManager


class BaseFrameworkDetector(ABC):
    """Abstract base class for modular framework detection."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the framework."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category (e.g. Mobile, Frontend, Backend, Full Stack)."""
        pass

    @abstractmethod
    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        """Examines the scan context and returns a FrameworkMetric if detected."""
        pass


class FlutterDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "Flutter"

    @property
    def category(self) -> str:
        return "Mobile"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        # Check pubspec.yaml for flutter sdk or flutter dependency
        if "pubspec.yaml" not in ctx.files_set:
            return None

        is_flutter = False
        version = None
        has_dart = any(f.endswith(".dart") for f in ctx.relative_files)

        # Check dependencies for flutter
        for dep in ctx.dependencies:
            if dep.name.lower() == "flutter":
                is_flutter = True
                version = dep.version
                break

        # Fallback inspection of pubspec.yaml
        if not is_flutter:
            try:
                content = ctx.security.safe_read_text(ctx.root_dir / "pubspec.yaml")
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    if "flutter" in data or "flutter" in data.get("dependencies", {}):
                        is_flutter = True
            except Exception:
                pass

        if is_flutter or (has_dart and ("android" in ctx.relative_dirs or "ios" in ctx.relative_dirs)):
            confidence = 1.0 if is_flutter else 0.8
            return FrameworkMetric(
                name=self.name,
                version=version,
                category=self.category,
                confidence=confidence,
            )
        return None


class ReactDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "React"

    @property
    def category(self) -> str:
        return "Frontend"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        version = None
        has_react_dep = False

        for dep in ctx.dependencies:
            if dep.name.lower() == "react":
                has_react_dep = True
                version = dep.version
                break

        has_react_files = any(f.endswith(".jsx") or f.endswith(".tsx") for f in ctx.relative_files)

        if has_react_dep or (has_react_files and "package.json" in ctx.files_set):
            confidence = 1.0 if has_react_dep else 0.85
            return FrameworkMetric(
                name=self.name,
                version=version,
                category=self.category,
                confidence=confidence,
            )
        return None


class NextJsDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "Next.js"

    @property
    def category(self) -> str:
        return "Full Stack"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        version = None
        has_next_dep = False

        for dep in ctx.dependencies:
            if dep.name.lower() == "next":
                has_next_dep = True
                version = dep.version
                break

        has_next_config = any(
            f.startswith("next.config.") or "/next.config." in f for f in ctx.files_set
        )

        if has_next_dep or has_next_config:
            confidence = 1.0 if (has_next_dep and has_next_config) else 0.95
            return FrameworkMetric(
                name=self.name,
                version=version,
                category=self.category,
                confidence=confidence,
            )
        return None


class NodeJsDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "Node.js"

    @property
    def category(self) -> str:
        return "Backend / Runtime"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        if "package.json" not in ctx.files_set:
            return None

        # Detect Node.js backend frameworks or presence of package.json
        has_js_ts = any(
            f.endswith((".js", ".ts", ".mjs", ".cjs")) for f in ctx.relative_files
        )
        if has_js_ts:
            return FrameworkMetric(
                name=self.name,
                version=None,
                category=self.category,
                confidence=0.9,
            )
        return None


class FastAPIDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "FastAPI"

    @property
    def category(self) -> str:
        return "Backend"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        version = None
        for dep in ctx.dependencies:
            if dep.name.lower() == "fastapi":
                version = dep.version
                return FrameworkMetric(
                    name=self.name,
                    version=version,
                    category=self.category,
                    confidence=1.0,
                )
        return None


class DjangoDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "Django"

    @property
    def category(self) -> str:
        return "Backend"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        version = None
        has_django_dep = False

        for dep in ctx.dependencies:
            if dep.name.lower() == "django":
                has_django_dep = True
                version = dep.version
                break

        has_manage_py = "manage.py" in ctx.files_set

        if has_django_dep or has_manage_py:
            confidence = 1.0 if (has_django_dep and has_manage_py) else 0.9
            return FrameworkMetric(
                name=self.name,
                version=version,
                category=self.category,
                confidence=confidence,
            )
        return None


class SpringBootDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return "Spring Boot"

    @property
    def category(self) -> str:
        return "Backend"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        version = None
        has_spring = False

        for dep in ctx.dependencies:
            name_lower = dep.name.lower()
            if "spring-boot" in name_lower or "org.springframework.boot" in name_lower:
                has_spring = True
                version = dep.version
                break

        # Check pom.xml or build.gradle content if not in parsed dependencies
        if not has_spring:
            for build_file in ("pom.xml", "build.gradle", "build.gradle.kts"):
                if build_file in ctx.files_set:
                    try:
                        content = ctx.security.safe_read_text(ctx.root_dir / build_file)
                        if "org.springframework.boot" in content or "spring-boot" in content:
                            has_spring = True
                            break
                    except Exception:
                        pass

        if has_spring:
            return FrameworkMetric(
                name=self.name,
                version=version,
                category=self.category,
                confidence=1.0,
            )
        return None


class DotNetDetector(BaseFrameworkDetector):
    @property
    def name(self) -> str:
        return ".NET"

    @property
    def category(self) -> str:
        return "Framework / Runtime"

    def detect(self, ctx: ScanContext) -> Optional[FrameworkMetric]:
        has_csproj = any(f.endswith(".csproj") for f in ctx.files_set)
        has_sln = any(f.endswith(".sln") for f in ctx.files_set)

        if has_csproj or has_sln:
            return FrameworkMetric(
                name=self.name,
                version=None,
                category=self.category,
                confidence=1.0,
            )
        return None


class FrameworkRegistry:
    """Registry coordinating all independent framework detectors."""

    def __init__(self) -> None:
        self.detectors: List[BaseFrameworkDetector] = [
            FlutterDetector(),
            NextJsDetector(),  # Next.js before React to accurately capture Next.js projects
            ReactDetector(),
            FastAPIDetector(),
            DjangoDetector(),
            SpringBootDetector(),
            DotNetDetector(),
            NodeJsDetector(),
        ]

    def register(self, detector: BaseFrameworkDetector) -> None:
        """Register a new framework detector dynamically."""
        self.detectors.append(detector)

    def detect_all(self, ctx: ScanContext) -> List[FrameworkMetric]:
        """Runs all registered detectors against the context."""
        detected: List[FrameworkMetric] = []
        seen_names: Set[str] = set()

        for detector in self.detectors:
            try:
                metric = detector.detect(ctx)
                if metric and metric.name not in seen_names:
                    detected.append(metric)
                    seen_names.add(metric.name)
            except Exception:
                pass

        return detected
