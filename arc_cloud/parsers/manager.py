"""Parser manager coordinating language AST parsers."""
from pathlib import Path
from typing import Dict, List, Optional

from arc_cloud.parsers.base import BaseParser, ParsedModule
from arc_cloud.parsers.python_parser import PythonParser


class ParserManager:
    """Manages language parsers and routes source files to appropriate parsers."""

    def __init__(self) -> None:
        self._parsers: List[BaseParser] = []
        # Register default parsers
        self.register_parser(PythonParser())

    def register_parser(self, parser: BaseParser) -> None:
        """Register a new language AST parser."""
        self._parsers.append(parser)

    def get_parser_for_file(self, file_path: Path) -> Optional[BaseParser]:
        """Find a parser that supports the given file path."""
        for parser in self._parsers:
            if parser.supports(file_path):
                return parser
        return None

    def parse_file(self, file_path: Path) -> Optional[ParsedModule]:
        """Parse file if supported by any registered parser; returns None if unsupported."""
        parser = self.get_parser_for_file(file_path)
        if parser:
            return parser.parse_file(file_path)
        return None
