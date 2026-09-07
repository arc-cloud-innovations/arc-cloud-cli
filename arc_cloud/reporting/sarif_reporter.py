"""SARIF v2.1.0 reporter for ARC CLOUD health reports."""
import json
from typing import Any, Dict, List

from arc_cloud.core.models import FindingSeverity, HealthReport


def _severity_to_sarif_level(severity: FindingSeverity) -> str:
    if severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH):
        return "error"
    elif severity == FindingSeverity.MEDIUM:
        return "warning"
    else:
        return "note"


class SARIFReporter:
    """Generates standard SARIF v2.1.0 reports for CI/CD and GitHub Code Scanning."""

    @staticmethod
    def render(report: HealthReport, indent: int = 2) -> str:
        data = SARIFReporter.to_dict(report)
        return json.dumps(data, indent=indent)

    @staticmethod
    def to_dict(report: HealthReport) -> Dict[str, Any]:
        # Collect distinct rules
        rules_map: Dict[str, Dict[str, Any]] = {}
        for f in report.findings:
            if f.rule_id not in rules_map:
                rules_map[f.rule_id] = {
                    "id": f.rule_id,
                    "name": f.title,
                    "shortDescription": {"text": f.title},
                    "fullDescription": {"text": f.description},
                    "defaultConfiguration": {
                        "level": _severity_to_sarif_level(f.severity)
                    },
                    "help": {
                        "text": f.recommendation or f.description,
                        "markdown": f"**Recommendation**: {f.recommendation}" if f.recommendation else f.description,
                    },
                }

        sarif_results: List[Dict[str, Any]] = []
        for f in report.findings:
            region: Dict[str, int] = {
                "startLine": max(1, f.line),
            }
            if f.col is not None and f.col > 0:
                region["startColumn"] = f.col + 1
            if f.end_line is not None and f.end_line >= f.line:
                region["endLine"] = f.end_line
            if f.end_col is not None and f.end_col > 0:
                region["endColumn"] = f.end_col + 1

            sarif_results.append({
                "ruleId": f.rule_id,
                "level": _severity_to_sarif_level(f.severity),
                "message": {"text": f.description},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f.file_path,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": region,
                        }
                    }
                ],
            })

        sarif_doc: Dict[str, Any] = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "ARC CLOUD",
                            "semanticVersion": "0.1.0",
                            "informationUri": "https://github.com/arc-cloud-innovations/arc-cloud-cli",
                            "rules": list(rules_map.values()),
                        }
                    },
                    "results": sarif_results,
                }
            ],
        }
        return sarif_doc
