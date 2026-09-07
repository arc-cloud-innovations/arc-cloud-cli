"""JSON reporter for ARC CLOUD health reports."""
import json
from typing import Any, Dict

from arc_cloud.core.models import HealthReport


class JSONReporter:
    """Serializes HealthReport into clean, valid JSON format."""

    @staticmethod
    def to_dict(report: HealthReport) -> Dict[str, Any]:
        """Converts HealthReport to standard dictionary with compatibility keys."""
        data = report.model_dump()
        # Ensure convenience aliases are present in exported dictionary
        data["project_profile"] = data.get("project", {})

        health_dict = dict(data.get("health", {}))
        health_dict["overall_score"] = float(health_dict.get("overall_health", 100))
        if health_dict.get("code_quality") is not None:
            health_dict["code_quality_score"] = float(health_dict["code_quality"])
        else:
            health_dict["code_quality_score"] = None
        data["health_score"] = health_dict

        data["risk_assessment"] = data.get("risk", {})
        return data

    @staticmethod
    def render(report: HealthReport, indent: int = 2) -> str:
        """Serializes HealthReport to formatted JSON string."""
        return json.dumps(JSONReporter.to_dict(report), indent=indent, default=str)
