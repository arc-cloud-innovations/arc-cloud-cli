"""ARC001: Excessive Function Complexity Rule."""
from typing import List

from arc_cloud.core.models import Finding, FindingCategory, FindingSeverity
from arc_cloud.rules.base import BaseRule, RuleContext


class ARC001ExcessiveComplexityRule(BaseRule):
    """Detects functions with cyclomatic complexity exceeding configured thresholds."""

    rule_id = "ARC001"
    title = "Excessive Function Complexity"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.MEDIUM
    description = (
        "Calculates McCabe cyclomatic complexity of functions and methods. Functions with "
        "high complexity have too many execution paths, making them error-prone, hard to test, "
        "and difficult to maintain."
    )
    recommendation = (
        "Refactor this function into smaller, single-purpose helper functions. "
        "Replace deeply nested if/else statements with guard clauses, dictionary dispatch, "
        "or polymorphism."
    )
    why_it_matters = (
        "High cyclomatic complexity correlates strongly with defect density and regression rates. "
        "Functions with complexity > 10 require significantly more test cases to achieve adequate branch coverage."
    )
    example_bad = """def process_transaction(data):
    if data:
        if data.get('type') == 'A':
            for item in data.get('items', []):
                if item.get('valid'):
                    if item.get('amount') > 100:
                        # nested logic...
                        pass"""
    example_good = """def process_transaction(data):
    if not data or data.get('type') != 'A':
        return
    for item in data.get('items', []):
        process_item(item)"""

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []

        if not context.parsed_module or context.parsed_module.has_error:
            return findings

        # Determine threshold from config or default to 10
        threshold = 10
        if context.config and context.config.code_quality:
            threshold = context.config.code_quality.max_complexity

        # Read lines for snippet extraction if available
        lines = []
        if context.file_content:
            lines = context.file_content.splitlines()

        for fn in context.parsed_module.all_functions():
            if fn.cyclomatic_complexity > threshold:
                # Severity scaling based on how severely complexity exceeds threshold
                if fn.cyclomatic_complexity >= 25:
                    severity = FindingSeverity.CRITICAL
                elif fn.cyclomatic_complexity >= 15:
                    severity = FindingSeverity.HIGH
                elif fn.cyclomatic_complexity > threshold:
                    severity = FindingSeverity.MEDIUM
                else:
                    severity = FindingSeverity.LOW

                snippet = None
                if lines and 1 <= fn.line <= len(lines):
                    # extract 1-3 lines around the function definition
                    snippet = "\n".join(lines[fn.line - 1 : min(len(lines), fn.line + 2)])

                qualifier = f"Method '{fn.class_name}.{fn.name}'" if fn.is_method and fn.class_name else f"Function '{fn.name}'"

                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        description=(
                            f"{qualifier} has cyclomatic complexity of {fn.cyclomatic_complexity}, "
                            f"exceeding threshold of {threshold}."
                        ),
                        category=self.category,
                        severity=severity,
                        file_path=context.relative_path,
                        line=fn.line,
                        end_line=fn.end_line,
                        col=max(1, fn.col + 1),
                        end_col=max(1, fn.end_col + 1) if fn.end_col is not None else None,
                        recommendation=self.recommendation,
                        code_snippet=snippet,
                    )
                )

        return findings
