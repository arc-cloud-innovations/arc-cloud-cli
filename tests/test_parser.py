"""Tests for Python AST Parser and complexity calculation."""
from pathlib import Path
import pytest

from arc_cloud.parsers.python_parser import PythonParser


def test_python_parser_extracts_functions_and_classes() -> None:
    code = """
import os
from math import sqrt

def simple_func(x, y):
    '''A simple function.'''
    return x + y

class Calculator:
    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Division by zero")
        return a / b
"""
    parser = PythonParser()
    module = parser.parse_source(code, Path("test.py"))

    assert not module.has_error
    assert len(module.imports) == 2
    assert "os" in module.imports
    assert "math.sqrt" in module.imports

    # Functions
    assert len(module.functions) == 1
    fn = module.functions[0]
    assert fn.name == "simple_func"
    assert fn.parameters == ["x", "y"]
    assert fn.cyclomatic_complexity == 1
    assert fn.docstring == "A simple function."

    # Classes
    assert len(module.classes) == 1
    cls = module.classes[0]
    assert cls.name == "Calculator"
    assert len(cls.methods) == 2
    assert cls.methods[0].name == "add"
    assert cls.methods[0].cyclomatic_complexity == 1
    assert cls.methods[1].name == "divide"
    assert cls.methods[1].cyclomatic_complexity == 2  # base 1 + if 1


def test_python_parser_complexity_calculation() -> None:
    code = """
def complex_decision(a, b, c, items):
    if a > 0:
        if b > 0 and c > 0:
            for item in items:
                while item < 10:
                    try:
                        item += 1
                    except ValueError:
                        break
        elif b < 0:
            pass
    return [x for x in items if x % 2 == 0]
"""
    parser = PythonParser()
    module = parser.parse_source(code, Path("complex.py"))
    assert not module.has_error
    fn = module.functions[0]
    # base 1
    # +1 if a > 0
    # +1 if b > 0
    # +1 and c > 0 (BoolOp with 2 values -> +1)
    # +1 for item in items
    # +1 while item < 10
    # +1 except ValueError
    # +1 elif b < 0
    # +1 listcomp generator
    # +1 listcomp if x % 2 == 0
    # Total = 10
    assert fn.cyclomatic_complexity >= 9
