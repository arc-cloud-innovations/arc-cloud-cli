"""Project Intelligence Detector identifying ecosystem components."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from arc_cloud.scanner.dependencies import DependencyDetector
from arc_cloud.scanner.frameworks import FrameworkRegistry, ScanContext
from arc_cloud.scanner.languages import LanguageDetector
from arc_cloud.scanner.platforms import PlatformDetector
from arc_cloud.utils.security import SecurityManager


class ProjectDetector:
    """Detects languages, frameworks, package managers, and build systems."""

    def __init__(self, root_dir: Path, security: SecurityManager):
        self.root_dir = root_dir
        self.security = security
        self.framework_registry = FrameworkRegistry()

    def detect(self, all_files: List[str], relative_dirs: List[str]) -> Dict[str, Any]:
        file_set = set(all_files)
        dir_set = set(relative_dirs)

        # 1. Languages
        lang_metrics = LanguageDetector.detect(all_files)
        languages = [{"name": l.name, "files": l.files, "percentage": l.percentage} for l in lang_metrics]
        primary_lang = lang_metrics[0].name if lang_metrics else None

        # 2. Dependencies & Frameworks
        dep_detector = DependencyDetector(root_dir=self.root_dir, security=self.security)
        dependencies = dep_detector.detect(all_files)

        ctx = ScanContext(
            root_dir=self.root_dir,
            relative_files=all_files,
            relative_dirs=relative_dirs,
            dependencies=dependencies,
            files_set=file_set,
            security=self.security,
        )
        framework_metrics = self.framework_registry.detect_all(ctx)
        frameworks = [{"name": f.name, "version": f.version, "category": f.category} for f in framework_metrics]

        # 3. Package Managers
        package_managers: Set[str] = set()
        if "package-lock.json" in file_set or "package.json" in file_set:
            package_managers.add("npm")
        if "yarn.lock" in file_set:
            package_managers.add("yarn")
        if "pnpm-lock.yaml" in file_set:
            package_managers.add("pnpm")
        if "requirements.txt" in file_set or "pyproject.toml" in file_set:
            package_managers.add("pip")
        if "Pipfile" in file_set or "Pipfile.lock" in file_set:
            package_managers.add("pipenv")
        if "pubspec.yaml" in file_set or "pubspec.lock" in file_set:
            package_managers.add("pub")
        if "pom.xml" in file_set:
            package_managers.add("maven")
        if any(f in ("build.gradle", "build.gradle.kts") for f in file_set):
            package_managers.add("gradle")
        if any(f.endswith(".csproj") for f in file_set):
            package_managers.add("nuget")

        # 4. Build Systems
        build_systems: Set[str] = set()
        if any("dockerfile" in f.lower() for f in file_set):
            build_systems.add("Docker")
        if "Makefile" in file_set:
            build_systems.add("Make")
        if any("gradle" in f for f in file_set):
            build_systems.add("Gradle")
        if "pom.xml" in file_set:
            build_systems.add("Maven")
        if any("vite.config" in f for f in file_set):
            build_systems.add("Vite")
        if any("next.config" in f for f in file_set):
            build_systems.add("Next.js Build")

        # 5. Project Type Classification
        project_type = self._classify_project_type(framework_metrics, primary_lang, file_set, dir_set)

        return {
            "languages": languages,
            "primary_language": primary_lang,
            "frameworks": frameworks,
            "package_managers": sorted(list(package_managers)),
            "build_systems": sorted(list(build_systems)),
            "project_type": project_type,
        }

    def _classify_project_type(
        self,
        frameworks: list,
        primary_language: Optional[str],
        file_set: Set[str],
        dir_set: Set[str],
    ) -> str:
        names = {f.name.lower() for f in frameworks}
        if "flutter" in names or "android" in dir_set or "ios" in dir_set:
            return "Mobile Application"
        if "next.js" in names:
            return "Full Stack"
        if any(n in names for n in ("react", "vue", "angular")):
            return "Web Application"
        if any(n in names for n in ("fastapi", "django", "spring boot", "node.js")):
            return "Backend"
        if any(f in ("setup.py", "pyproject.toml") for f in file_set) and any(f.startswith("src/") for f in file_set):
            return "Library"
        if primary_language in ("Python", "Java", "Go", "Rust", "C#"):
            return "Backend"
        if primary_language in ("JavaScript", "TypeScript"):
            return "Web Application"
        if primary_language in ("Dart", "Swift", "Kotlin"):
            return "Mobile Application"
        return "Unknown"
