"""Python AST parser for ARC CLOUD static analysis."""
import ast
from pathlib import Path
from typing import List, Optional, Any

from arc_cloud.parsers.base import BaseParser, ParsedClass, ParsedFunction, ParsedModule


class _ComplexityVisitor(ast.NodeVisitor):
    """Calculates cyclomatic complexity of an AST subtree (e.g. a function body)."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each operand after the first adds a decision path: (A and B and C) -> +2
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        # Each generator adds 1, each 'if' clause adds 1
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: Any) -> None:
        # Python 3.10+ match statement
        if hasattr(node, "cases"):
            for case in node.cases:
                self.complexity += 1
        self.generic_visit(node)

    # Note: Nested functions/lambdas have their own separate complexity scope
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Do not recurse into nested function complexity for the outer function
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass


def compute_node_complexity(node: ast.AST) -> int:
    """Compute cyclomatic complexity for a function AST node."""
    visitor = _ComplexityVisitor()
    for child in ast.iter_child_nodes(node):
        visitor.visit(child)
    return visitor.complexity


class PythonParser(BaseParser):
    """AST parser for Python files (.py, .pyi, .pyw)."""

    SUPPORTED_EXTENSIONS = {".py", ".pyi", ".pyw"}

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse_file(self, file_path: Path) -> ParsedModule:
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
            return self.parse_source(code, file_path)
        except Exception as e:
            return ParsedModule(
                file_path=file_path,
                language="Python",
                parse_error=str(e),
            )

    def parse_source(self, code: str, file_path: Path) -> ParsedModule:
        loc = len([l for l in code.splitlines() if l.strip()])
        try:
            tree = ast.parse(code, filename=str(file_path))
        except SyntaxError as e:
            return ParsedModule(
                file_path=file_path,
                language="Python",
                total_loc=loc,
                parse_error=f"SyntaxError at line {e.lineno}: {e.msg}",
            )
        except Exception as e:
            return ParsedModule(
                file_path=file_path,
                language="Python",
                total_loc=loc,
                parse_error=str(e),
            )

        module = ParsedModule(
            file_path=file_path,
            language="Python",
            total_loc=loc,
            raw_ast=tree,
        )

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed_fn = self._parse_function(node, is_method=False)
                module.functions.append(parsed_fn)
            elif isinstance(node, ast.ClassDef):
                parsed_cls = self._parse_class(node)
                module.classes.append(parsed_cls)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    module.imports.append(f"{mod}.{alias.name}" if mod else alias.name)

        return module

    def _parse_function(
        self,
        node: ast.AST,
        is_method: bool = False,
        class_name: Optional[str] = None,
    ) -> ParsedFunction:
        is_async = isinstance(node, ast.AsyncFunctionDef)
        name = getattr(node, "name", "<anonymous>")
        line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", line)
        col = getattr(node, "col_offset", 0)
        end_col = getattr(node, "end_col_offset", 0)

        params: List[str] = []
        if hasattr(node, "args"):
            for arg in node.args.args:
                params.append(arg.arg)

        docstring = ast.get_docstring(node)
        complexity = compute_node_complexity(node)
        loc = max(1, end_line - line + 1)

        return ParsedFunction(
            name=name,
            line=line,
            end_line=end_line,
            col=col,
            end_col=end_col,
            cyclomatic_complexity=complexity,
            loc=loc,
            is_async=is_async,
            is_method=is_method,
            class_name=class_name,
            parameters=params,
            docstring=docstring,
        )

    def _parse_class(self, node: ast.ClassDef) -> ParsedClass:
        line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", line)
        base_classes: List[str] = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                base_classes.append(b.id)
            elif isinstance(b, ast.Attribute):
                base_classes.append(getattr(b, "attr", "Unknown"))

        methods: List[ParsedFunction] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed_method = self._parse_function(
                    item, is_method=True, class_name=node.name
                )
                methods.append(parsed_method)

        return ParsedClass(
            name=node.name,
            line=line,
            end_line=end_line,
            methods=methods,
            base_classes=base_classes,
        )
