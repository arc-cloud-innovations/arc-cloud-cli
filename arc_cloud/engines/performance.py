"""Performance Intelligence Engine for ARC CLOUD (static performance bottlenecks)."""
import ast
import time
from pathlib import Path
from typing import List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult


class PerformanceEngine(BaseEngine):
    """Detects static performance risks, nested iterations, and redundant work in loops."""

    name = "performance"
    version = "1.0.0"
    category = FindingCategory.PERFORMANCE

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
        files_checked = 0

        for rel_path in profile.source_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            if abs_path.suffix.lower() in (".py", ".pyi"):
                files_checked += 1
                try:
                    tree = ast.parse(abs_path.read_text(encoding="utf-8", errors="replace"))
                    self._check_ast_performance(tree, rel_path, findings)
                except Exception:
                    pass

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics={"files_checked": files_checked, "performance_issues_found": len(findings)},
            execution_time_ms=elapsed_ms,
        )

    def _check_ast_performance(self, tree: ast.AST, rel_path: str, findings: List[Finding]) -> None:
        for node in ast.walk(tree):
            # 1. Deeply nested loops (O(n^3) or deeper)
            if isinstance(node, (ast.For, ast.While)):
                inner_depth = self._get_loop_nesting_depth(node)
                if inner_depth >= 3:
                    findings.append(
                        Finding(
                            rule_id="ARC-PERF-001",
                            engine=self.name,
                            title="Excessive Loop Nesting (O(n^3)+ Complexity)",
                            description=f"Loop nesting depth of {inner_depth} detected. Triple or deeper nested loops create exponential CPU bottlenecks on large datasets.",
                            category=self.category,
                            severity=FindingSeverity.HIGH if inner_depth >= 4 else FindingSeverity.MEDIUM,
                            file_path=rel_path,
                            line=getattr(node, "lineno", 1),
                            recommendation="Restructure logic using hash maps, sets for O(1) lookups, or vectorization.",
                            confidence="HIGH",
                            estimated_fix_minutes=30,
                        )
                    )

            # 2. Compiling regex or opening files inside loops
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Regex compilation inside loop
                        if isinstance(child.func, ast.Attribute) and child.func.attr == "compile":
                            if isinstance(child.func.value, ast.Name) and child.func.value.id == "re":
                                findings.append(
                                    Finding(
                                        rule_id="ARC-PERF-002",
                                        engine=self.name,
                                        title="Regex Compilation Inside Loop",
                                        description="Regular expression 're.compile(...)' called inside loop re-parses regex patterns on every iteration.",
                                        category=self.category,
                                        severity=FindingSeverity.MEDIUM,
                                        file_path=rel_path,
                                        line=getattr(child, "lineno", 1),
                                        recommendation="Compile regex once as a module-level constant before loop execution.",
                                        confidence="HIGH",
                                        estimated_fix_minutes=10,
                                    )
                                )

    def _get_loop_nesting_depth(self, node: ast.AST) -> int:
        max_depth = 1
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                max_depth = max(max_depth, 1 + self._get_loop_nesting_depth(child))
            else:
                for sub in ast.iter_child_nodes(child):
                    if isinstance(sub, (ast.For, ast.While)):
                        max_depth = max(max_depth, 1 + self._get_loop_nesting_depth(sub))
        return max_depth
