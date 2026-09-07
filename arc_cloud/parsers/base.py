"""Base parser interfaces and data structures for ARC CLOUD static analysis."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Any, Dict


@dataclass
class ParsedFunction:
    """Represents a function or method parsed from source code."""
    name: str
    line: int
    end_line: int
    col: int
    end_col: int
    cyclomatic_complexity: int = 1
    loc: int = 1
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ParsedClass:
    """Represents a class parsed from source code."""
    name: str
    line: int
    end_line: int
    methods: List[ParsedFunction] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)


@dataclass
class ParsedModule:
    """Represents the parsed structure of a single file."""
    file_path: Path
    language: str
    functions: List[ParsedFunction] = field(default_factory=list)
    classes: List[ParsedClass] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    total_loc: int = 0
    raw_ast: Optional[Any] = None
    parse_error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        return self.parse_error is not None

    def all_functions(self) -> List[ParsedFunction]:
        """Returns all functions including methods inside classes."""
        all_funcs = list(self.functions)
        for cls in self.classes:
            all_funcs.extend(cls.methods)
        return all_funcs


class BaseParser(ABC):
    """Abstract base class for language AST parsers."""

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Return True if this parser supports the given file."""
        pass

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParsedModule:
        """Parse a file from disk into a ParsedModule."""
        pass

    @abstractmethod
    def parse_source(self, code: str, file_path: Path) -> ParsedModule:
        """Parse source code string into a ParsedModule."""
        pass
