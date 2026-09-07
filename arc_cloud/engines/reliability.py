"""Reliability analysis engine for ARC CLOUD."""
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


class ReliabilityEngine(BaseEngine):
    """Analyzes runtime reliability risks, exception hygiene, and resource management."""

    name = "reliability"
    version = "1.0.0"
    category = FindingCategory.RELIABILITY

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

            # Currently support Python and inspect text/AST
            if abs_path.suffix.lower() in (".py", ".pyi"):
                files_checked += 1
                try:
                    code = abs_path.read_text(encoding="utf-8", errors="replace")
                    tree = ast.parse(code, filename=str(abs_path))
                    self._check_ast(tree, rel_path, findings)
                except Exception:
                    pass

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics={"files_checked": files_checked, "issues_found": len(findings)},
            execution_time_ms=elapsed_ms,
        )

    def _check_ast(self, tree: ast.AST, rel_path: str, findings: List[Finding]) -> None:
        for node in ast.walk(tree):
            # 1. Broad or suppressed exceptions
            if isinstance(node, ast.ExceptHandler):
                line = getattr(node, "lineno", 1)
                is_bare = node.type is None
                is_broad = False
                if node.type:
                    if isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                        is_broad = True

                # Check if body is just 'pass' or '...'
                is_suppressed = False
                if len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Pass):
                        is_suppressed = True
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
                        is_suppressed = True

                if is_bare or (is_broad and is_suppressed):
                    findings.append(
                        Finding(
                            rule_id="ARC-REL-001",
                            engine=self.name,
                            title="Suppressed Broad Exception",
                            description="Silencing all exceptions with bare 'except:' or 'except Exception: pass' hides critical runtime failures.",
                            category=self.category,
                            severity=FindingSeverity.HIGH if is_bare else FindingSeverity.MEDIUM,
                            file_path=rel_path,
                            line=line,
                            recommendation="Catch specific exceptions and log the error context or re-raise.",
                            confidence="HIGH",
                            estimated_fix_minutes=15,
                        )
                    )

            # 2. Unclosed resource pattern: file = open(...) not in with statement
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "open":
                    line = getattr(node, "lineno", 1)
                    findings.append(
                        Finding(
                            rule_id="ARC-REL-002",
                            engine=self.name,
                            title="Unsafe Resource Allocation",
                            description="File opened via direct assignment without context manager ('with open(...)') risks resource/file descriptor leaks.",
                            category=self.category,
                            severity=FindingSeverity.MEDIUM,
                            file_path=rel_path,
                            line=line,
                            recommendation="Use 'with open(...) as f:' context manager to ensure automatic closure.",
                            confidence="HIGH",
                            estimated_fix_minutes=10,
                        )
                    )
