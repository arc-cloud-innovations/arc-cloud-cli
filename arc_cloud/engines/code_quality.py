"""Code Quality analysis engine for ARC CLOUD."""
import time
from pathlib import Path
from typing import List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import Finding, FindingCategory, ProjectProfile
from arc_cloud.engines.base import BaseEngine, EngineResult
from arc_cloud.parsers.manager import ParserManager
from arc_cloud.rules.base import RuleContext
from arc_cloud.rules.registry import RuleRegistry


class CodeQualityEngine(BaseEngine):
    """Analyzes code quality metrics, complexity, and AST structure."""

    name = "code_quality"
    version = "1.0.0"
    category = FindingCategory.CODE_QUALITY

    def __init__(
        self,
        parser_manager: Optional[ParserManager] = None,
        rule_registry: Optional[RuleRegistry] = None,
    ) -> None:
        self.parser_manager = parser_manager or ParserManager()
        self.rule_registry = rule_registry or RuleRegistry()

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start_time = time.perf_counter()
        findings: List[Finding] = []
        files_analyzed = 0
        total_functions_analyzed = 0

        # Retrieve active code quality rules
        cq_rules = self.rule_registry.get_by_category(FindingCategory.CODE_QUALITY)

        # Iterate over source files discovered in the index
        for rel_path in profile.source_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            parsed_module = self.parser_manager.parse_file(abs_path)
            if not parsed_module:
                continue

            files_analyzed += 1
            total_functions_analyzed += len(parsed_module.all_functions())

            file_content = None
            try:
                file_content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

            context = RuleContext(
                project_root=project_root,
                file_path=abs_path,
                relative_path=rel_path,
                parsed_module=parsed_module,
                profile=profile,
                config=config,
                file_content=file_content,
            )

            for rule in cq_rules:
                rule_findings = rule.evaluate(context)
                findings.extend(rule_findings)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status="completed",
            findings=findings,
            metrics={
                "files_analyzed": files_analyzed,
                "functions_analyzed": total_functions_analyzed,
            },
            execution_time_ms=elapsed_ms,
        )
