"""Architecture Intelligence Engine for ARC CLOUD."""
import ast
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult


class ArchitectureEngine(BaseEngine):
    """Analyzes package modules, layering compliance, and circular dependencies."""

    name = "architecture"
    version = "1.0.0"
    category = FindingCategory.ARCHITECTURE

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

        # 1. Identify module directories from project_tree
        module_dirs = [d for d in profile.project_tree.keys() if d not in (".", "")]
        module_count = len(module_dirs)

        # 2. Extract import graph between top-level modules
        import_graph: Dict[str, Set[str]] = {}
        file_to_module: Dict[str, str] = {}

        for rel_path in profile.source_files:
            parts = Path(rel_path).parts
            mod = parts[0] if len(parts) > 1 else "."
            file_to_module[rel_path] = mod
            if mod not in import_graph:
                import_graph[mod] = set()

            abs_path = project_root / rel_path
            if abs_path.suffix.lower() in (".py", ".pyi") and abs_path.is_file():
                try:
                    tree = ast.parse(abs_path.read_text(encoding="utf-8", errors="replace"))
                    for node in ast.walk(tree):
                        imported_pkg = ""
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported_pkg = alias.name.split(".")[0]
                                if imported_pkg in profile.project_tree:
                                    import_graph[mod].add(imported_pkg)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            imported_pkg = node.module.split(".")[0]
                            if imported_pkg in profile.project_tree:
                                import_graph[mod].add(imported_pkg)

                        # Check Layer Violation (e.g. UI/view layer directly importing db/storage/repository)
                        if any(ui_term in rel_path.lower() for ui_term in ("ui", "views", "screens", "pages", "presentation")):
                            if any(db_term in imported_pkg.lower() for db_term in ("db", "database", "models", "repository", "sql")):
                                findings.append(
                                    Finding(
                                        rule_id="ARC-ARCH-002",
                                        engine=self.name,
                                        title="Architecture Layer Violation",
                                        description=f"Presentation layer '{rel_path}' directly imports data/database package '{imported_pkg}'.",
                                        category=self.category,
                                        severity=FindingSeverity.HIGH,
                                        file_path=rel_path,
                                        line=getattr(node, "lineno", 1),
                                        recommendation="Route data requests through the Service / Controller layer instead of coupling UI to database.",
                                        confidence="HIGH",
                                        estimated_fix_minutes=45,
                                    )
                                )
                except Exception:
                    pass

        # 3. Detect Circular Dependencies between modules
        circular_pairs: List[tuple[str, str]] = []
        for mod_a, targets in import_graph.items():
            for mod_b in targets:
                if mod_b != mod_a and mod_a in import_graph.get(mod_b, set()):
                    pair = tuple(sorted([mod_a, mod_b]))
                    if pair not in circular_pairs:
                        circular_pairs.append(pair)
                        findings.append(
                            Finding(
                                rule_id="ARC-ARCH-001",
                                engine=self.name,
                                title="Circular Module Dependency",
                                description=f"Circular dependency detected between module '{pair[0]}' and module '{pair[1]}'.",
                                category=self.category,
                                severity=FindingSeverity.HIGH,
                                file_path=pair[0],
                                line=1,
                                recommendation="Decouple cyclic dependency using dependency inversion, interfaces, or a shared common module.",
                                confidence="HIGH",
                                estimated_fix_minutes=60,
                            )
                        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metrics: Dict[str, Any] = {
            "modules_count": module_count,
            "circular_dependencies": len(circular_pairs),
            "layer_violations": sum(1 for f in findings if f.rule_id == "ARC-ARCH-002"),
            "pattern": "Layered / Modular Architecture" if module_count > 3 else "Monolithic / Single-Package",
        }

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics=metrics,
            execution_time_ms=elapsed_ms,
        )
