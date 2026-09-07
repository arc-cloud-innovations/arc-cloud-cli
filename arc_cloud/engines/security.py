"""Security analysis engine for ARC CLOUD (SAST)."""
import ast
import re
import time
from pathlib import Path
from typing import List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult


class SecurityEngine(BaseEngine):
    """Static Application Security Testing (SAST) engine."""

    name = "security"
    version = "1.0.0"
    category = FindingCategory.SECURITY

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        findings: List[Finding] = []
        files_checked = 0

        for rel_path in profile.source_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            files_checked += 1
            content = ""
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Python AST security checks
            if abs_path.suffix.lower() in (".py", ".pyi"):
                try:
                    tree = ast.parse(content, filename=str(abs_path))
                    self._check_python_ast(tree, rel_path, findings)
                except Exception:
                    pass

            # General regex patterns (insecure HTTP, etc.)
            self._check_regex_security(content, rel_path, findings)

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics={"files_checked": files_checked, "vulnerabilities_found": len(findings)},
            execution_time_ms=elapsed_ms,
        )

    def _check_python_ast(self, tree: ast.AST, rel_path: str, findings: List[Finding]) -> None:
        for node in ast.walk(tree):
            # ARC-SEC-005: Unsafe Eval / Exec
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    findings.append(
                        Finding(
                            rule_id="ARC-SEC-005",
                            engine=self.name,
                            title="Unsafe Dynamic Execution (eval/exec)",
                            description=f"Use of dynamic '{node.func.id}()' allows arbitrary code execution if inputs are untrusted.",
                            category=self.category,
                            severity=FindingSeverity.CRITICAL,
                            file_path=rel_path,
                            line=getattr(node, "lineno", 1),
                            recommendation="Replace eval/exec with safe parsing (e.g. ast.literal_eval, json.loads) or explicit logic.",
                            confidence="HIGH",
                            estimated_fix_minutes=30,
                        )
                    )

            # ARC-SEC-003: Command Injection via shell=True
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name in ("Popen", "run", "call", "check_call", "check_output", "system"):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            findings.append(
                                Finding(
                                    rule_id="ARC-SEC-003",
                                    engine=self.name,
                                    title="Command Injection Risk (shell=True)",
                                    description="Subprocess executed with shell=True is vulnerable to command injection if command strings incorporate user input.",
                                    category=self.category,
                                    severity=FindingSeverity.HIGH,
                                    file_path=rel_path,
                                    line=getattr(node, "lineno", 1),
                                    recommendation="Pass command arguments as a list of strings and set shell=False.",
                                    confidence="HIGH",
                                    estimated_fix_minutes=20,
                                )
                            )

            # ARC-SEC-007: Weak Cryptography (MD5, SHA1)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("md5", "sha1"):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "hashlib":
                        findings.append(
                            Finding(
                                rule_id="ARC-SEC-007",
                                engine=self.name,
                                title="Weak Cryptographic Hash (MD5/SHA1)",
                                description=f"Algorithm 'hashlib.{node.func.attr}()' is cryptographically broken and vulnerable to collision attacks.",
                                category=self.category,
                                severity=FindingSeverity.MEDIUM,
                                file_path=rel_path,
                                line=getattr(node, "lineno", 1),
                                recommendation="Use modern secure hashing algorithms such as SHA-256 (hashlib.sha256) or bcrypt/argon2 for passwords.",
                                confidence="HIGH",
                                estimated_fix_minutes=15,
                            )
                        )

            # ARC-SEC-002: SQL Injection Risk (execute with formatted string or SQL assignment)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "execute":
                    if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                        findings.append(
                            Finding(
                                rule_id="ARC-SEC-002",
                                engine=self.name,
                                title="Potential SQL Injection Risk",
                                description="SQL query constructed via string formatting/concatenation instead of parameterized query arguments.",
                                category=self.category,
                                severity=FindingSeverity.HIGH,
                                file_path=rel_path,
                                line=getattr(node, "lineno", 1),
                                recommendation="Use parameterized queries (e.g. cursor.execute('SELECT * FROM t WHERE id = ?', (id,))) instead of raw strings.",
                                confidence="MEDIUM",
                                estimated_fix_minutes=25,
                            )
                        )
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and any(kw in target.id.lower() for kw in ("sql", "query")):
                        if isinstance(node.value, (ast.JoinedStr, ast.BinOp)):
                            findings.append(
                                Finding(
                                    rule_id="ARC-SEC-002",
                                    engine=self.name,
                                    title="Potential SQL Injection Risk",
                                    description="SQL query constructed via dynamic string formatting/concatenation.",
                                    category=self.category,
                                    severity=FindingSeverity.HIGH,
                                    file_path=rel_path,
                                    line=getattr(node, "lineno", 1),
                                    recommendation="Use parameterized queries instead of string concatenation.",
                                    confidence="HIGH",
                                    estimated_fix_minutes=25,
                                )
                            )

    def _check_regex_security(self, content: str, rel_path: str, findings: List[Finding]) -> None:
        lines = content.splitlines()
        url_pattern = re.compile(r"""["']http://([a-zA-Z0-9_\-\.]+)(?:/|\b|["'])""")
        for idx, line in enumerate(lines, 1):
            # ARC-SEC-008: Insecure HTTP API URL
            match = url_pattern.search(line)
            if match and not line.strip().startswith("#") and not line.strip().startswith("//"):
                host = match.group(1).lower()
                if host not in ("localhost", "127.0.0.1") and not host.startswith("schemas.") and not host.endswith("w3.org"):
                        findings.append(
                            Finding(
                                rule_id="ARC-SEC-008",
                                engine=self.name,
                                title="Insecure HTTP Communication",
                                description="Unencrypted HTTP endpoint detected. Data transmitted in cleartext is vulnerable to interception and tampering.",
                                category=self.category,
                                severity=FindingSeverity.MEDIUM,
                                file_path=rel_path,
                                line=idx,
                                recommendation="Upgrade connection to HTTPS (TLS encryption).",
                                confidence="MEDIUM",
                                estimated_fix_minutes=10,
                            )
                        )
                        break  # Report once per file
