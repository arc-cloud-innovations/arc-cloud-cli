"""ARC CLOUD Local HTML Report Generator."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from arc_cloud.core.models import HealthReport, EngineStatus


class HTMLReporter:
    """Generates a standalone, responsive, zero-dependency HTML health report."""

    def __init__(self, report: HealthReport):
        self.report = report

    def render(self) -> str:
        rep = self.report
        proj = rep.project_profile
        health = rep.health_score
        risk = rep.risk_profile

        # Date formatting
        scanned_at = rep.scanned_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Color helpers
        def grade_color(grade: str) -> str:
            if grade == "A":
                return "#10b981"
            if grade == "B":
                return "#3b82f6"
            if grade == "C":
                return "#f59e0b"
            if grade == "D":
                return "#f97316"
            return "#ef4444"

        def status_badge(status: Any) -> str:
            st_val = status.value if hasattr(status, "value") else str(status)
            if st_val == "ANALYZED":
                return '<span class="badge badge-success">ANALYZED</span>'
            elif st_val == "NOT_ANALYZED":
                return '<span class="badge badge-warning">NOT ANALYZED</span>'
            elif st_val == "UNSUPPORTED":
                return '<span class="badge badge-secondary">UNSUPPORTED</span>'
            else:
                return '<span class="badge badge-danger">ERROR</span>'

        def sev_badge(sev: str) -> str:
            sev_u = sev.upper()
            colors = {
                "CRITICAL": "badge-critical",
                "HIGH": "badge-high",
                "MEDIUM": "badge-medium",
                "LOW": "badge-low",
                "INFO": "badge-info",
            }
            cls = colors.get(sev_u, "badge-secondary")
            return f'<span class="badge {cls}">{sev_u}</span>'

        # Build Engines Rows
        engine_rows = []
        engine_names = [
            ("code_quality", "Code Quality"),
            ("reliability", "Reliability"),
            ("security", "Security"),
            ("secrets", "Secrets"),
            ("dependencies", "Dependencies"),
            ("architecture", "Architecture"),
            ("technical_debt", "Technical Debt"),
            ("testing", "Testing"),
            ("performance", "Performance"),
            ("ai_risk", "AI Risk"),
        ]

        for key, display in engine_names:
            status = health.engine_statuses.get(key, EngineStatus.NOT_ANALYZED)
            score_val = getattr(health, key, None)
            if isinstance(score_val, (int, float)):
                score_str = f"{score_val:.0f}/100"
                grade = "A" if score_val >= 90 else "B" if score_val >= 80 else "C" if score_val >= 70 else "D" if score_val >= 60 else "F"
            elif score_val is not None:
                score_str = str(score_val)
                grade = "—"
            else:
                score_str = "—"
                grade = "—"
            
            # Count findings
            findings_count = sum(1 for f in rep.findings if getattr(f, "engine", "").lower() == key.lower())
            grade_style = f'color: {grade_color(grade)}; font-weight: bold;' if grade != "—" else 'color: #94a3b8;'

            engine_rows.append(f"""
            <tr>
                <td><strong>{display}</strong></td>
                <td>{status_badge(status)}</td>
                <td>{score_str}</td>
                <td style="{grade_style}">{grade}</td>
                <td>{findings_count}</td>
            </tr>
            """)

        # Build Findings Rows
        finding_rows = []
        for i, f in enumerate(rep.findings):
            fid = html.escape(f.id)
            rule = html.escape(f.rule_id)
            engine = html.escape(getattr(f, "engine", "code_quality"))
            sev = f.severity.value
            msg = html.escape(f.message)
            fp = html.escape(str(f.file_path))
            line = f.line or 1
            rec = html.escape(f.recommendation or "No recommendation provided.")
            code_snippet = f.code_snippet or ""
            snippet_html = f"<pre><code>{html.escape(code_snippet)}</code></pre>" if code_snippet else "<em>No code snippet available</em>"
            fix_time = f"{f.estimated_fix_minutes} min" if getattr(f, "estimated_fix_minutes", None) else "—"

            finding_rows.append(f"""
            <tr class="finding-row" data-engine="{engine.lower()}" data-severity="{sev.lower()}">
                <td><button class="expand-btn" onclick="toggleDetails({i})">+</button></td>
                <td><code>{fid}</code></td>
                <td><code>{rule}</code></td>
                <td><span class="engine-tag">{engine}</span></td>
                <td>{sev_badge(sev)}</td>
                <td>{fp}:{line}</td>
                <td>{msg}</td>
            </tr>
            <tr id="details-{i}" class="finding-details" style="display: none;">
                <td colspan="7">
                    <div class="details-box">
                        <p><strong>Remediation:</strong> {rec}</p>
                        <p><strong>Estimated Fix Time:</strong> {fix_time}</p>
                        <div class="snippet-box">
                            <strong>Snippet:</strong>
                            {snippet_html}
                        </div>
                    </div>
                </td>
            </tr>
            """)

        # Recommendations list
        recs_html = []
        if rep.recommendations:
            for rank, rec in enumerate(rep.recommendations, 1):
                recs_html.append(f"<li><strong>#{rank}</strong> {html.escape(rec)}</li>")
        else:
            recs_html.append("<li>No immediate critical recommendations. Great job!</li>")

        # Tech Debt breakdown
        debt = rep.technical_debt_estimate or {}
        debt_hours = debt.get("estimated_hours", 0.0)
        debt_categories = debt.get("categories", {})
        debt_cat_html = " ".join([
            f'<span class="cat-chip"><strong>{html.escape(k.capitalize())}:</strong> {v}h</span>'
            for k, v in debt_categories.items()
        ])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARC CLOUD Health Report — {html.escape(proj.name)}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --critical: #ef4444;
            --high: #f97316;
            --medium: #f59e0b;
            --low: #3b82f6;
            --info: #06b6d4;
            --success: #10b981;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .header-title h1 {{
            font-size: 1.875rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }}
        .header-title h1 span {{
            color: var(--primary);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .stat-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }}
        .stat-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
        }}
        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .section h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--text);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            margin-top: 0.5rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        th {{
            color: var(--text-muted);
            font-weight: 600;
            background: rgba(15, 23, 42, 0.4);
        }}
        tr:hover {{
            background: var(--surface-hover);
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-success {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
        .badge-secondary {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #64748b; }}
        .badge-critical {{ background: #ef4444; color: #fff; }}
        .badge-high {{ background: #f97316; color: #fff; }}
        .badge-medium {{ background: #f59e0b; color: #000; }}
        .badge-low {{ background: #3b82f6; color: #fff; }}
        .badge-info {{ background: #06b6d4; color: #000; }}
        .engine-tag {{
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-family: monospace;
        }}
        .filter-controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .filter-controls input, .filter-controls select {{
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .expand-btn {{
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }}
        .details-box {{
            padding: 1rem;
            background: rgba(15, 23, 42, 0.8);
            border-radius: 6px;
            margin: 0.5rem 0;
        }}
        .details-box p {{
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }}
        .snippet-box pre {{
            background: #090d16;
            padding: 0.75rem;
            border-radius: 4px;
            overflow-x: auto;
            margin-top: 0.25rem;
            border: 1px solid var(--border);
            font-size: 0.85rem;
        }}
        .cat-chip {{
            display: inline-block;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            margin-right: 0.5rem;
            margin-top: 0.5rem;
            font-size: 0.85rem;
        }}
        .rec-list {{
            list-style: none;
            padding: 0;
        }}
        .rec-list li {{
            padding: 0.75rem;
            border-left: 3px solid var(--primary);
            background: rgba(15, 23, 42, 0.4);
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
            font-size: 0.95rem;
        }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 0; }}
            .section, header {{ border: 1px solid #ccc; background: #fff; color: #000; box-shadow: none; }}
            .stat-card {{ background: #f9f9f9; border: 1px solid #ccc; }}
            .filter-controls {{ display: none; }}
            .expand-btn {{ display: none; }}
            .finding-details {{ display: table-row !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <div>
                    <h1>ARC CLOUD <span>HEALTH REPORT</span></h1>
                    <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.25rem;">
                        Project: <strong>{html.escape(proj.name)}</strong> | 
                        Type: <strong>{html.escape(proj.architecture_type)}</strong> | 
                        Language: <strong>{html.escape(proj.primary_language)}</strong>
                    </p>
                </div>
                <div style="text-align: right; color: var(--text-muted); font-size: 0.85rem;">
                    Scanned at: {scanned_at}<br>
                    Files: <strong>{proj.total_files}</strong> | Lines: <strong>{proj.total_lines:,}</strong>
                </div>
            </div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Health Score</div>
                    <div class="stat-value" style="color: {grade_color(health.letter_grade)};">
                        {health.overall_score:.0f}/100 ({health.letter_grade})
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Risk Profile</div>
                    <div class="stat-value" style="color: {sev_badge(risk.risk_level)};">
                        {risk.overall_risk_score:.0f} ({risk.risk_level.upper()})
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Findings</div>
                    <div class="stat-value">{len(rep.findings)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Coverage</div>
                    <div class="stat-value">{html.escape(health.analysis_coverage)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Technical Debt</div>
                    <div class="stat-value">{debt_hours:.1f} hrs</div>
                </div>
            </div>
        </header>

        <section class="section">
            <h2>Engineering Health Matrix (10 Engines)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Engine Name</th>
                        <th>Analysis Status</th>
                        <th>Score</th>
                        <th>Grade</th>
                        <th>Findings Count</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(engine_rows)}
                </tbody>
            </table>
        </section>

        <section class="section">
            <h2>Risk Profile Breakdown</h2>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <div class="stat-card" style="flex: 1; min-width: 140px;">
                    <div class="stat-label">Critical</div>
                    <div class="stat-value" style="color: var(--critical);">{risk.critical_count}</div>
                </div>
                <div class="stat-card" style="flex: 1; min-width: 140px;">
                    <div class="stat-label">High</div>
                    <div class="stat-value" style="color: var(--high);">{risk.high_count}</div>
                </div>
                <div class="stat-card" style="flex: 1; min-width: 140px;">
                    <div class="stat-label">Medium</div>
                    <div class="stat-value" style="color: var(--medium);">{risk.medium_count}</div>
                </div>
                <div class="stat-card" style="flex: 1; min-width: 140px;">
                    <div class="stat-label">Low</div>
                    <div class="stat-value" style="color: var(--low);">{risk.low_count}</div>
                </div>
                <div class="stat-card" style="flex: 1; min-width: 140px;">
                    <div class="stat-label">Info</div>
                    <div class="stat-value" style="color: var(--info);">{risk.info_count}</div>
                </div>
            </div>
        </section>

        <section class="section">
            <h2>Technical Debt & Prioritized Actions</h2>
            <p style="margin-bottom: 0.5rem; color: var(--text-muted); font-size: 0.9rem;">
                Estimated remediation time: <strong>{debt_hours:.1f} hours</strong>
            </p>
            <div style="margin-bottom: 1.5rem;">
                {debt_cat_html}
            </div>
            <h3 style="font-size: 1rem; margin-bottom: 0.75rem;">Top Prioritized Actions</h3>
            <ul class="rec-list">
                {"".join(recs_html)}
            </ul>
        </section>

        <section class="section">
            <h2>Detailed Findings ({len(rep.findings)})</h2>
            <div class="filter-controls">
                <input type="text" id="searchInput" placeholder="Search message, file, rule..." onkeyup="filterFindings()">
                <select id="engineFilter" onchange="filterFindings()">
                    <option value="">All Engines</option>
                    <option value="code_quality">Code Quality</option>
                    <option value="reliability">Reliability</option>
                    <option value="security">Security</option>
                    <option value="secrets">Secrets</option>
                    <option value="dependencies">Dependencies</option>
                    <option value="architecture">Architecture</option>
                    <option value="technical_debt">Technical Debt</option>
                    <option value="testing">Testing</option>
                    <option value="performance">Performance</option>
                    <option value="ai_risk">AI Risk</option>
                </select>
                <select id="severityFilter" onchange="filterFindings()">
                    <option value="">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="info">Info</option>
                </select>
            </div>
            <div style="overflow-x: auto;">
                <table id="findingsTable">
                    <thead>
                        <tr>
                            <th style="width: 40px;"></th>
                            <th>Finding ID</th>
                            <th>Rule ID</th>
                            <th>Engine</th>
                            <th>Severity</th>
                            <th>Location</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(finding_rows) if finding_rows else '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No findings detected! Platform is healthy.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </section>
    </div>

    <script>
        function toggleDetails(index) {{
            const el = document.getElementById('details-' + index);
            if (el.style.display === 'none') {{
                el.style.display = 'table-row';
            }} else {{
                el.style.display = 'none';
            }}
        }}

        function filterFindings() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const engine = document.getElementById('engineFilter').value.toLowerCase();
            const severity = document.getElementById('severityFilter').value.toLowerCase();

            const rows = document.querySelectorAll('.finding-row');
            rows.forEach((row, i) => {{
                const rowEngine = row.getAttribute('data-engine') || '';
                const rowSev = row.getAttribute('data-severity') || '';
                const text = row.innerText.toLowerCase();

                const matchSearch = !search || text.includes(search);
                const matchEngine = !engine || rowEngine === engine;
                const matchSev = !severity || rowSev === severity;

                const detailsRow = document.getElementById('details-' + i);
                if (matchSearch && matchEngine && matchSev) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                    if (detailsRow) detailsRow.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
        return html_content

    def write_to_file(self, destination: Path) -> None:
        """Writes rendered HTML report to target destination file."""
        html_code = self.render()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html_code, encoding="utf-8")
