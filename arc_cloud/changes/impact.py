"""Impact analysis mapping changed files to affected modules, tests, and dependencies."""
from __future__ import annotations

from pathlib import Path
from typing import List, Set

from arc_cloud.changes.models import ImpactedScope

DEPENDENCY_MANIFESTS = {
    "pubspec.yaml",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Pipfile",
    "setup.py",
}

CONFIG_FILES = {
    ".arccloud.yml",
    ".arccloud.yaml",
    "tsconfig.json",
    ".env",
    "Dockerfile",
    "docker-compose.yml",
    "vite.config.ts",
    "next.config.js",
}


class ImpactAnalyzer:
    """Analyzes the blast radius and affected scope of code changes."""

    @classmethod
    def analyze_file(cls, root_dir: Path, file_path: Path) -> ImpactedScope:
        scope = ImpactedScope()
        file_name = file_path.name

        if file_name in DEPENDENCY_MANIFESTS:
            scope.is_dependency_manifest = True
        if file_name in CONFIG_FILES or file_name.endswith(".config.js") or file_name.endswith(".config.ts"):
            scope.is_config_file = True

        # Module name derivation
        try:
            rel = file_path.relative_to(root_dir)
            module_name = ".".join(rel.with_suffix("").parts)
            scope.affected_modules.append(module_name)
        except Exception:
            scope.affected_modules.append(file_path.stem)

        # Detect candidate tests
        scope.affected_tests = cls.find_candidate_tests(root_dir, file_path)
        return scope

    @classmethod
    def find_candidate_tests(cls, root_dir: Path, source_file: Path) -> List[Path]:
        stem = source_file.stem
        suffix = source_file.suffix
        candidate_names = {
            f"test_{stem}{suffix}",
            f"{stem}_test{suffix}",
            f"{stem}.test{suffix}",
            f"{stem}.spec{suffix}",
        }

        found_tests: Set[Path] = set()
        test_dirs = [root_dir / "tests", root_dir / "test", root_dir / "__tests__"]

        for tdir in test_dirs:
            if tdir.is_dir():
                for cname in candidate_names:
                    # Look for direct match or match anywhere in test dir
                    direct = tdir / cname
                    if direct.is_file():
                        found_tests.add(direct)
                    for match in tdir.glob(f"**/{cname}"):
                        if match.is_file():
                            found_tests.add(match)

        # Also look in same directory as source file (e.g. React/Jest colocation)
        parent_dir = source_file.parent
        for cname in candidate_names:
            co = parent_dir / cname
            if co.is_file():
                found_tests.add(co)

        return sorted(list(found_tests))
