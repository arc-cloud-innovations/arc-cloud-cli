"""Scanner Engine coordinating static analysis and blueprint generation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Set

from arc_cloud import __version__
from arc_cloud.blueprint.generator import BlueprintGenerator
from arc_cloud.blueprint.models import (
    ArchitectureSummary,
    Blueprint,
    FrameworkMetric,
    LanguageMetric,
    PlatformInfo,
    PlatformType,
    ProjectType,
)
from arc_cloud.scanner.config_detector import ConfigDetector
from arc_cloud.scanner.dependencies import DependencyDetector
from arc_cloud.scanner.frameworks import FrameworkRegistry, ScanContext
from arc_cloud.scanner.languages import LanguageDetector
from arc_cloud.scanner.platforms import PlatformDetector
from arc_cloud.scanner.structure import StructureAnalyzer
from arc_cloud.utils.filesystem import SafeProjectWalker, ScanWalkResult
from arc_cloud.utils.security import SecurityManager


class ScannerEngine:
    """Orchestrates static analysis without code execution."""

    def __init__(
        self,
        max_files: int = 20_000,
        max_depth: int = 20,
        max_file_size: int = 10_000_000,
    ) -> None:
        self.max_files = max_files
        self.max_depth = max_depth
        self.max_file_size = max_file_size
        self.framework_registry = FrameworkRegistry()

    def scan(self, target_path: str | Path) -> Blueprint:
        start_time = time.perf_counter()
        project_dir = Path(target_path).resolve()

        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: '{project_dir}'")

        if not project_dir.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: '{project_dir}'")

        # Safe traversal
        walker = SafeProjectWalker(
            root_dir=project_dir,
            max_files=self.max_files,
            max_depth=self.max_depth,
            max_file_size=self.max_file_size,
        )
        walk_result: ScanWalkResult = walker.walk()
        warnings = list(walk_result.warnings)

        if not walk_result.files and not walk_result.directories:
            warnings.append("⚠ Project directory appears to be empty.")

        security = walker.security

        # 1. Detect Languages
        languages = LanguageDetector.detect(walk_result.relative_files)

        # 2. Detect Dependencies
        dep_detector = DependencyDetector(root_dir=project_dir, security=security)
        dependencies = dep_detector.detect(walk_result.relative_files)

        # 3. Detect Frameworks
        scan_ctx = ScanContext(
            root_dir=project_dir,
            relative_files=walk_result.relative_files,
            relative_dirs=walk_result.relative_dirs,
            dependencies=dependencies,
            files_set=set(walk_result.relative_files),
            security=security,
        )
        frameworks = self.framework_registry.detect_all(scan_ctx)

        # 4. Detect Platforms
        platforms = PlatformDetector.detect(
            relative_dirs=walk_result.relative_dirs,
            relative_files=walk_result.relative_files,
        )

        # 5. Detect Configuration Files
        configs = ConfigDetector.detect(walk_result.relative_files)

        # 6. Analyze Structure
        structure = StructureAnalyzer.analyze(
            relative_dirs=walk_result.relative_dirs,
            total_files=walk_result.total_files_found,
            total_dirs=walk_result.total_dirs_found,
            ignored_dirs=walk_result.ignored_directories_encountered,
        )

        # 7. Classify Project Type
        project_type = self._classify_project_type(
            frameworks=frameworks,
            platforms=platforms,
            languages=languages,
            relative_files=walk_result.relative_files,
            dependencies=dependencies,
        )

        # 8. Analyze Architecture Indicators
        architecture = self._analyze_architecture(
            walk_result=walk_result,
            frameworks=frameworks,
            configs=configs,
        )

        duration = time.perf_counter() - start_time
        project_name = project_dir.name

        return BlueprintGenerator.create(
            project_name=project_name,
            project_type=project_type,
            root_path=str(project_dir),
            languages=languages,
            frameworks=frameworks,
            platforms=platforms,
            dependencies=dependencies,
            configuration_files=configs,
            structure=structure,
            architecture=architecture,
            warnings=warnings,
            duration_seconds=duration,
            files_scanned=walk_result.total_files_found,
            scanner_version=__version__,
        )

    def _classify_project_type(
        self,
        frameworks: List[FrameworkMetric],
        platforms: List[PlatformInfo],
        languages: List[LanguageMetric],
        relative_files: List[str],
        dependencies: list,
    ) -> ProjectType:
        """Determines the strongest project classification based on static signals."""
        framework_names = {f.name.lower() for f in frameworks}
        platform_names = {p.name for p in platforms}

        # Mobile check: Flutter or explicit mobile platforms
        if "flutter" in framework_names:
            return ProjectType.MOBILE

        if PlatformType.ANDROID in platform_names or PlatformType.IOS in platform_names:
            if not ("next.js" in framework_names or "react" in framework_names):
                return ProjectType.MOBILE

        # Full Stack check: Next.js or combinations of frontend & backend
        if "next.js" in framework_names:
            return ProjectType.FULL_STACK

        has_frontend = bool(framework_names.intersection({"react", "vue", "angular", "svelte"}))
        has_backend = bool(
            framework_names.intersection(
                {"fastapi", "django", "spring boot", "express", "nest", "node.js"}
            )
        )

        if has_frontend and has_backend:
            return ProjectType.FULL_STACK

        # Dedicated Web Application
        if has_frontend or PlatformType.WEB in platform_names:
            return ProjectType.WEB

        # Dedicated Backend
        if has_backend:
            return ProjectType.BACKEND

        # CLI Tool check
        dep_names = {d.name.lower() for d in dependencies}
        cli_signals = {"typer", "click", "argparse", "commander", "yargs", "cobra", "clap"}
        if dep_names.intersection(cli_signals):
            return ProjectType.CLI

        # .NET project type heuristic
        if ".net" in framework_names:
            return ProjectType.BACKEND

        # Library check
        if any(f in ("setup.py", "pyproject.toml") for f in relative_files):
            if any(f.startswith("src/") or f.startswith("lib/") for f in relative_files):
                return ProjectType.LIBRARY

        if not languages and not frameworks:
            return ProjectType.UNKNOWN

        # Default fallback based on primary language
        if languages:
            top_lang = languages[0].name
            if top_lang in ("Python", "Java", "Go", "Rust", "C#"):
                return ProjectType.BACKEND
            elif top_lang in ("JavaScript", "TypeScript"):
                return ProjectType.WEB
            elif top_lang in ("Dart", "Swift", "Kotlin"):
                return ProjectType.MOBILE

        return ProjectType.UNKNOWN

    def _analyze_architecture(
        self,
        walk_result: ScanWalkResult,
        frameworks: List[FrameworkMetric],
        configs: list,
    ) -> ArchitectureSummary:
        patterns: List[str] = []
        details: dict = {}

        # Containerized
        has_docker = any("docker" in c.name.lower() for c in configs)
        if has_docker:
            patterns.append("Containerized (Docker)")
            details["containerized"] = True

        # Monorepo / Multi-package
        pkg_manifest_count = sum(
            1 for f in walk_result.relative_files if Path(f).name in ("package.json", "pom.xml", "pubspec.yaml")
        )
        if pkg_manifest_count > 2:
            patterns.append("Monorepo / Multi-module")
            details["multi_module"] = True

        # Layered architecture (e.g. controllers, services, repositories)
        dirs = [d.lower() for d in walk_result.relative_dirs]
        has_layers = any(
            any(layer in d for layer in ("controller", "service", "repository", "model", "view", "route"))
            for d in dirs
        )
        if has_layers:
            patterns.append("Layered / Modular Architecture")
            details["layered"] = True

        # Test coverage setup
        has_tests = any(
            any(t in d for t in ("test", "tests", "spec", "__tests__")) for d in dirs
        )
        if has_tests:
            details["test_suite_detected"] = True

        return ArchitectureSummary(patterns=patterns, details=details)
