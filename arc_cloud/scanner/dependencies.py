"""Dependency detector and parser for ARC CLOUD CLI."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from arc_cloud.blueprint.models import DependencyInfo
from arc_cloud.utils.security import SecurityManager


class DependencyDetector:
    """Safely inspects project manifests to extract declared dependencies without code execution."""

    def __init__(self, root_dir: Path, security: SecurityManager):
        self.root_dir = root_dir
        self.security = security

    def detect(self, relative_files: List[str]) -> List[DependencyInfo]:
        dependencies: List[DependencyInfo] = []
        files_set = set(relative_files)

        # 1. Flutter / Dart: pubspec.yaml
        if "pubspec.yaml" in files_set:
            dependencies.extend(self._parse_pubspec(self.root_dir / "pubspec.yaml"))

        # 2. Node.js / JavaScript / TypeScript: package.json (root or immediate subdirs)
        for rel_file in relative_files:
            if Path(rel_file).name == "package.json" and len(Path(rel_file).parts) <= 3:
                dependencies.extend(self._parse_package_json(self.root_dir / rel_file, rel_file))

        # 3. Python: requirements.txt, pyproject.toml, Pipfile
        for rel_file in relative_files:
            p = Path(rel_file)
            if p.name == "requirements.txt" or p.name.startswith("requirements-") and p.suffix == ".txt":
                dependencies.extend(self._parse_requirements_txt(self.root_dir / rel_file, rel_file))
            elif p.name == "pyproject.toml":
                dependencies.extend(self._parse_pyproject_toml(self.root_dir / rel_file, rel_file))
            elif p.name == "Pipfile":
                dependencies.extend(self._parse_pipfile(self.root_dir / rel_file, rel_file))

        # 4. Java / Kotlin / Gradle / Maven: pom.xml, build.gradle, build.gradle.kts
        for rel_file in relative_files:
            p = Path(rel_file)
            if p.name == "pom.xml":
                dependencies.extend(self._parse_pom_xml(self.root_dir / rel_file, rel_file))
            elif p.name in ("build.gradle", "build.gradle.kts"):
                dependencies.extend(self._parse_build_gradle(self.root_dir / rel_file, rel_file))

        # 5. .NET: *.csproj
        for rel_file in relative_files:
            if rel_file.endswith(".csproj"):
                dependencies.extend(self._parse_csproj(self.root_dir / rel_file, rel_file))

        # Deduplicate dependencies while preserving order
        unique_deps: List[DependencyInfo] = []
        seen: set[tuple[str, str, str]] = set()
        for dep in dependencies:
            key = (dep.name.lower(), dep.source, dep.type or "runtime")
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps

    def _parse_pubspec(self, file_path: Path) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return deps

            for name, spec in data.get("dependencies", {}).items():
                if isinstance(spec, str):
                    ver = spec
                elif isinstance(spec, dict) and "version" in spec:
                    ver = str(spec["version"])
                elif isinstance(spec, dict) and "sdk" in spec:
                    ver = f"sdk: {spec['sdk']}"
                else:
                    ver = None
                deps.append(DependencyInfo(name=name, version=ver, source="pubspec.yaml", type="runtime"))

            for name, spec in data.get("dev_dependencies", {}).items():
                if isinstance(spec, str):
                    ver = spec
                elif isinstance(spec, dict) and "version" in spec:
                    ver = str(spec["version"])
                else:
                    ver = None
                deps.append(DependencyInfo(name=name, version=ver, source="pubspec.yaml", type="dev"))
        except Exception:
            pass
        return deps

    def _parse_package_json(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            data = json.loads(content)
            if not isinstance(data, dict):
                return deps

            for name, ver in data.get("dependencies", {}).items():
                deps.append(DependencyInfo(name=name, version=str(ver), source=rel_source, type="runtime"))

            for name, ver in data.get("devDependencies", {}).items():
                deps.append(DependencyInfo(name=name, version=str(ver), source=rel_source, type="dev"))

            for name, ver in data.get("peerDependencies", {}).items():
                deps.append(DependencyInfo(name=name, version=str(ver), source=rel_source, type="peer"))
        except Exception:
            pass
        return deps

    def _parse_requirements_txt(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-r") or line.startswith("-i"):
                    continue

                # Pattern matching package names and optional version specifiers
                match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", line)
                if match:
                    name = match.group(1).strip()
                    ver = match.group(2).strip() or None
                    deps.append(DependencyInfo(name=name, version=ver, source=rel_source, type="runtime"))
        except Exception:
            pass
        return deps

    def _parse_pyproject_toml(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            # Simple TOML parser or regex-based fallback without external tomllib dependencies
            import tomllib  # Built-in in Python 3.11+
            content = self.security.safe_read_text(file_path)
            data = tomllib.loads(content)

            # PEP 621 dependencies
            project_deps = data.get("project", {}).get("dependencies", [])
            if isinstance(project_deps, list):
                for item in project_deps:
                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", item.strip())
                    if match:
                        name = match.group(1).strip()
                        ver = match.group(2).strip() or None
                        deps.append(DependencyInfo(name=name, version=ver, source=rel_source, type="runtime"))

            # Poetry dependencies
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            if isinstance(poetry_deps, dict):
                for name, ver in poetry_deps.items():
                    if name.lower() == "python":
                        continue
                    version_str = ver if isinstance(ver, str) else str(ver.get("version", ""))
                    deps.append(DependencyInfo(name=name, version=version_str or None, source=rel_source, type="runtime"))
        except Exception:
            pass
        return deps

    def _parse_pipfile(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            import tomllib
            content = self.security.safe_read_text(file_path)
            data = tomllib.loads(content)

            for name, ver in data.get("packages", {}).items():
                ver_str = ver if isinstance(ver, str) else None
                deps.append(DependencyInfo(name=name, version=ver_str, source=rel_source, type="runtime"))

            for name, ver in data.get("dev-packages", {}).items():
                ver_str = ver if isinstance(ver, str) else None
                deps.append(DependencyInfo(name=name, version=ver_str, source=rel_source, type="dev"))
        except Exception:
            pass
        return deps

    def _parse_pom_xml(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            # Remove namespaces for easy parsing
            xml_content = re.sub(r'\sxmlns="[^"]+"', '', content, count=1)
            root = ET.fromstring(xml_content)

            for dep in root.findall(".//dependency"):
                group = dep.findtext("groupId", "").strip()
                artifact = dep.findtext("artifactId", "").strip()
                version = dep.findtext("version", "").strip() or None
                scope = dep.findtext("scope", "runtime").strip()

                if artifact:
                    name = f"{group}:{artifact}" if group else artifact
                    deps.append(DependencyInfo(name=name, version=version, source=rel_source, type=scope))
        except Exception:
            pass
        return deps

    def _parse_build_gradle(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            # Match dependencies like: implementation 'org.springframework.boot:spring-boot-starter-web:3.2.0'
            # or: implementation("org.springframework.boot:spring-boot-starter-web")
            pattern = re.compile(
                r'(implementation|api|compileOnly|runtimeOnly|testImplementation)\s*[\(\'\"]([a-zA-Z0-9_\.\-]+:[a-zA-Z0-9_\.\-]+(?::[a-zA-Z0-9_\.\-]+)?)[\)\'\"]'
            )
            for line in content.splitlines():
                line = line.strip()
                match = pattern.search(line)
                if match:
                    scope = match.group(1)
                    coord = match.group(2)
                    parts = coord.split(":")
                    if len(parts) >= 2:
                        name = f"{parts[0]}:{parts[1]}"
                        ver = parts[2] if len(parts) > 2 else None
                        dep_type = "test" if "test" in scope.lower() else "runtime"
                        deps.append(DependencyInfo(name=name, version=ver, source=rel_source, type=dep_type))
        except Exception:
            pass
        return deps

    def _parse_csproj(self, file_path: Path, rel_source: str) -> List[DependencyInfo]:
        deps: List[DependencyInfo] = []
        try:
            content = self.security.safe_read_text(file_path)
            root = ET.fromstring(content)
            for pkg in root.findall(".//PackageReference"):
                name = pkg.attrib.get("Include") or pkg.attrib.get("Update")
                version = pkg.attrib.get("Version")
                if name:
                    deps.append(DependencyInfo(name=name, version=version, source=rel_source, type="runtime"))
        except Exception:
            pass
        return deps
