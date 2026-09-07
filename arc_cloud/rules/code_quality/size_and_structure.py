"""Code quality rules for size, nesting, and structure."""
import ast
from typing import List, Optional

from arc_cloud.core.models import Finding, FindingCategory, FindingSeverity
from arc_cloud.rules.base import BaseRule, RuleContext


class ARC002LongFunctionRule(BaseRule):
    """Detects excessively long functions and methods."""
    rule_id = "ARC002"
    title = "Long Function"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.LOW
    description = (
        "Functions exceeding 50 lines of code become difficult to comprehend, maintain, "
        "and test thoroughly."
    )
    recommendation = "Decompose into smaller helper functions with distinct responsibilities."
    why_it_matters = "Short functions improve readability and make unit testing straightforward."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.parsed_module or context.parsed_module.has_error:
            return findings

        for fn in context.parsed_module.all_functions():
            if fn.loc > 50:
                severity = FindingSeverity.HIGH if fn.loc > 200 else (FindingSeverity.MEDIUM if fn.loc > 100 else FindingSeverity.LOW)
                qualifier = f"Method '{fn.class_name}.{fn.name}'" if fn.is_method and fn.class_name else f"Function '{fn.name}'"
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        engine="code_quality",
                        title=self.title,
                        description=f"{qualifier} has {fn.loc} lines of code (threshold: 50).",
                        category=self.category,
                        severity=severity,
                        file_path=context.relative_path,
                        line=fn.line,
                        end_line=fn.end_line,
                        col=max(1, fn.col + 1),
                        recommendation=self.recommendation,
                        confidence="HIGH",
                        estimated_fix_minutes=20,
                    )
                )
        return findings


class ARC003DeepNestingRule(BaseRule):
    """Detects deeply nested blocks within functions."""
    rule_id = "ARC003"
    title = "Deep Nesting"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.MEDIUM
    description = (
        "Nesting control structures (if/for/while/try) more than 4 levels deep leads to the 'Arrow Anti-Pattern', "
        "reducing readability."
    )
    recommendation = "Use early returns, guard clauses, or extract nested blocks into standalone functions."
    why_it_matters = "Deep nesting places high cognitive load on developers reading or debugging the code."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.parsed_module or not context.parsed_module.raw_ast:
            return findings

        tree = context.parsed_module.raw_ast
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                max_depth, deep_line = self._calculate_max_nesting(node)
                if max_depth > 4:
                    name = getattr(node, "name", "<anonymous>")
                    line = getattr(node, "lineno", 1)
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            engine="code_quality",
                            title=self.title,
                            description=f"Function '{name}' has nesting depth of {max_depth} (threshold: 4).",
                            category=self.category,
                            severity=FindingSeverity.HIGH if max_depth >= 7 else FindingSeverity.MEDIUM,
                            file_path=context.relative_path,
                            line=line,
                            col=getattr(node, "col_offset", 0) + 1,
                            recommendation=self.recommendation,
                            confidence="HIGH",
                            estimated_fix_minutes=25,
                        )
                    )
        return findings

    def _calculate_max_nesting(self, root_node: ast.AST) -> tuple[int, int]:
        max_depth = 0
        deepest_line = getattr(root_node, "lineno", 1)

        def walk_node(node: ast.AST, current_depth: int) -> None:
            nonlocal max_depth, deepest_line
            # Increase depth for control flow nodes
            is_nesting_node = isinstance(
                node,
                (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith)
            )
            new_depth = current_depth + 1 if is_nesting_node else current_depth
            if new_depth > max_depth:
                max_depth = new_depth
                deepest_line = getattr(node, "lineno", deepest_line)

            # Do not recurse into nested function bodies
            for child in ast.iter_child_nodes(node):
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk_node(child, new_depth)

        for child in ast.iter_child_nodes(root_node):
            walk_node(child, 0)
        return max_depth, deepest_line


class ARC006LargeClassRule(BaseRule):
    """Detects excessively large classes with too many lines."""
    rule_id = "ARC006"
    title = "Large Class"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.MEDIUM
    description = (
        "Classes with more than 300 lines of code frequently violate the Single Responsibility Principle."
    )
    recommendation = "Split the class into specialized classes or delegate functionality using composition."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.parsed_module or context.parsed_module.has_error:
            return findings

        for cls in context.parsed_module.classes:
            loc = cls.end_line - cls.line + 1
            if loc > 300:
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        engine="code_quality",
                        title=self.title,
                        description=f"Class '{cls.name}' has {loc} lines of code (threshold: 300).",
                        category=self.category,
                        severity=FindingSeverity.HIGH if loc > 600 else FindingSeverity.MEDIUM,
                        file_path=context.relative_path,
                        line=cls.line,
                        end_line=cls.end_line,
                        recommendation=self.recommendation,
                        confidence="HIGH",
                        estimated_fix_minutes=45,
                    )
                )
        return findings


class ARC007ExcessiveParametersRule(BaseRule):
    """Detects functions with excessive parameter lists."""
    rule_id = "ARC007"
    title = "Excessive Parameters"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.LOW
    description = (
        "Functions with more than 5 parameters are difficult to call, test, and maintain."
    )
    recommendation = "Group parameters into a dedicated data class, configuration object, or dictionary."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.parsed_module or context.parsed_module.has_error:
            return findings

        for fn in context.parsed_module.all_functions():
            param_count = len(fn.parameters)
            # Subtract 'self' or 'cls' if method
            if fn.is_method and fn.parameters and fn.parameters[0] in ("self", "cls"):
                param_count -= 1

            if param_count > 5:
                qualifier = f"Method '{fn.class_name}.{fn.name}'" if fn.is_method and fn.class_name else f"Function '{fn.name}'"
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        engine="code_quality",
                        title=self.title,
                        description=f"{qualifier} accepts {param_count} parameters (threshold: 5).",
                        category=self.category,
                        severity=FindingSeverity.MEDIUM if param_count > 8 else FindingSeverity.LOW,
                        file_path=context.relative_path,
                        line=fn.line,
                        col=max(1, fn.col + 1),
                        recommendation=self.recommendation,
                        confidence="HIGH",
                        estimated_fix_minutes=15,
                    )
                )
        return findings


class ARC011ExcessiveFileSizeRule(BaseRule):
    """Detects files that exceed reasonable line count thresholds."""
    rule_id = "ARC011"
    title = "Excessive File Size"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.LOW
    description = "Files exceeding 1,000 lines of code become maintainability hotspots."
    recommendation = "Split this file into separate cohesive modules or subpackages."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.file_content:
            return findings

        line_count = len(context.file_content.splitlines())
        if line_count > 1000:
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    engine="code_quality",
                    title=self.title,
                    description=f"File contains {line_count} lines of code (threshold: 1,000).",
                    category=self.category,
                    severity=FindingSeverity.MEDIUM if line_count > 2000 else FindingSeverity.LOW,
                    file_path=context.relative_path,
                    line=1,
                    recommendation=self.recommendation,
                    confidence="HIGH",
                    estimated_fix_minutes=30,
                )
            )
        return findings
