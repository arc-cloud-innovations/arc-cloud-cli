"""ARC CLOUD Finding and Rule Explanation Module (Offline-First / AI-Ready)."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional
from arc_cloud.ai.knowledge_base import RULE_KNOWLEDGE_BASE
from arc_cloud.core.models import Finding


class FindingExplainer:
    """Explains findings and rules with root-cause analysis and remediation guidance."""

    @classmethod
    def explain_rule(cls, rule_id: str, finding: Optional[Finding] = None) -> Dict[str, Any]:
        """Provides full structured explanation for a rule or finding."""
        rule_key = rule_id.strip()
        kb_entry = RULE_KNOWLEDGE_BASE.get(rule_key)

        # Prefix matching fallback (e.g. ARC-SEC-002 -> ARC-SEC)
        if not kb_entry:
            for k, v in RULE_KNOWLEDGE_BASE.items():
                if rule_key.startswith(k) or k.startswith(rule_key):
                    kb_entry = v
                    break

        if not kb_entry:
            # Fallback for unlisted rules
            engine = getattr(finding, "engine", "general") if finding else "general"
            title = finding.message if finding else f"Rule {rule_key}"
            kb_entry = {
                "title": title,
                "engine": engine,
                "root_cause": f"Detected code pattern violating static analysis standards for {rule_key}.",
                "impact": "May increase maintenance difficulty, cause unexpected runtime behavior, or introduce security/reliability risks.",
                "risk_if_not_fixed": "Accumulation of technical debt and potential bugs in production.",
                "remediation_steps": [
                    finding.recommendation if finding and finding.recommendation else "Refactor the affected code to follow language best practices.",
                    "Review surrounding logic to ensure edge cases are handled safely.",
                ],
                "code_before": finding.code_snippet if finding and finding.code_snippet else "# Inspect line in affected file",
                "code_after": "# Apply recommended refactoring pattern",
                "side_effects": "Ensure all callers and consumers are verified after refactoring.",
                "suggested_test": "Add a unit test covering this execution path.",
            }

        result = dict(kb_entry)
        result["rule_id"] = rule_key
        if finding:
            result["finding_id"] = finding.id
            result["file_path"] = str(finding.file_path)
            result["line"] = finding.line
            result["message"] = finding.message
            if finding.code_snippet:
                result["code_before"] = finding.code_snippet

        # If an external AI provider is configured and available, we can augment notes
        ai_provider = os.getenv("ARC_AI_PROVIDER")
        result["ai_enhanced"] = bool(ai_provider)
        result["provider"] = ai_provider or "offline-deterministic"

        return result
