"""Dependency Intelligence Engine for ARC CLOUD."""
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult


class DependencyEngine(BaseEngine):
    """Analyzes package manifests, dependency hygiene, and unpinned version risks."""

    name = "dependencies"
    version = "1.0.0"
    category = FindingCategory.DEPENDENCY

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        findings: List[Finding] = []
        direct_deps: List[str] = []
        unpinned_deps: List[str] = []

        manifests_found: List[str] = []

        # 1. Inspect package.json
        pkg_json = project_root / "package.json"
        if pkg_json.is_file():
            manifests_found.append("package.json")
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}
                for dep, ver in all_deps.items():
                    direct_deps.append(dep)
                    if ver in ("*", "latest") or ver.startswith("^") or ver.startswith(">"):
                        unpinned_deps.append(f"{dep} ({ver})")
            except Exception:
                pass

        # 2. Inspect requirements.txt
        req_txt = project_root / "requirements.txt"
        if req_txt.is_file():
            manifests_found.append("requirements.txt")
            try:
                for line_idx, line in enumerate(req_txt.read_text(encoding="utf-8").splitlines(), 1):
                    cleaned = line.strip().split("#")[0].strip()
                    if cleaned and not cleaned.startswith("-"):
                        direct_deps.append(cleaned)
                        if "==" not in cleaned and any(op in cleaned for op in (">=", ">", "~=", "*")):
                            unpinned_deps.append(cleaned)
            except Exception:
                pass

        # 3. Inspect pubspec.yaml
        pubspec = project_root / "pubspec.yaml"
        if pubspec.is_file():
            manifests_found.append("pubspec.yaml")
            try:
                data = yaml.safe_load(pubspec.read_text(encoding="utf-8")) or {}
                deps = data.get("dependencies", {})
                if isinstance(deps, dict):
                    for dep, ver in deps.items():
                        if dep != "flutter":
                            direct_deps.append(dep)
                            if ver in ("any", "*") or (isinstance(ver, str) and ver.startswith("^")):
                                unpinned_deps.append(f"{dep} ({ver})")
            except Exception:
                pass

        # 4. Generate findings for unpinned wildcard dependencies
        for unpinned in unpinned_deps:
            if "any" in unpinned or "*" in unpinned:
                findings.append(
                    Finding(
                        rule_id="ARC-DEP-001",
                        engine=self.name,
                        title="Unpinned Wildcard Dependency",
                        description=f"Dependency '{unpinned}' uses unpinned wildcard versioning, leading to non-reproducible builds.",
                        category=self.category,
                        severity=FindingSeverity.MEDIUM,
                        file_path=manifests_found[0] if manifests_found else "manifest",
                        line=1,
                        recommendation="Pin dependencies to specific version tags or ranges to prevent unexpected upstream breaking changes.",
                        confidence="HIGH",
                        estimated_fix_minutes=10,
                    )
                )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metrics: Dict[str, Any] = {
            "total_dependencies": len(direct_deps),
            "direct_dependencies": len(direct_deps),
            "unpinned_dependencies": len(unpinned_deps),
            "manifests_detected": manifests_found,
            "vulnerabilities": "NOT ANALYZED (No vulnerability database configured)",  # Honest metric, never fabricate CVEs
        }

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED if manifests_found else EngineStatus.UNSUPPORTED,
            findings=findings,
            metrics=metrics,
            execution_time_ms=elapsed_ms,
        )
