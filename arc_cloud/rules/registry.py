"""Rule registry for ARC CLOUD static analysis rules."""
from typing import Dict, List, Optional

from arc_cloud.core.models import FindingCategory
from arc_cloud.rules.base import BaseRule
from arc_cloud.rules.code_quality.complexity import ARC001ExcessiveComplexityRule
from arc_cloud.rules.code_quality.size_and_structure import (
    ARC002LongFunctionRule,
    ARC003DeepNestingRule,
    ARC006LargeClassRule,
    ARC007ExcessiveParametersRule,
    ARC011ExcessiveFileSizeRule,
)
from arc_cloud.rules.code_quality.duplication import ARC004DuplicateCodeRule


class RuleRegistry:
    """Registry that holds and queries analysis rules."""

    def __init__(self) -> None:
        self._rules: Dict[str, BaseRule] = {}
        # Auto-register core code quality rules
        self.register(ARC001ExcessiveComplexityRule())
        self.register(ARC002LongFunctionRule())
        self.register(ARC003DeepNestingRule())
        self.register(ARC004DuplicateCodeRule())
        self.register(ARC006LargeClassRule())
        self.register(ARC007ExcessiveParametersRule())
        self.register(ARC011ExcessiveFileSizeRule())

    def register(self, rule: BaseRule) -> None:
        """Register a new rule instance."""
        self._rules[rule.rule_id.upper()] = rule

    def get(self, rule_id: str) -> Optional[BaseRule]:
        """Look up a rule by its ID (case-insensitive)."""
        return self._rules.get(rule_id.strip().upper())

    def get_all(self) -> List[BaseRule]:
        """Return all registered rules."""
        return list(self._rules.values())

    def get_by_category(self, category: FindingCategory) -> List[BaseRule]:
        """Return rules filtered by category."""
        return [r for r in self._rules.values() if r.category == category]
