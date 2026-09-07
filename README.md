# ARC CLOUD — Software Engineering Health Platform CLI

[![CI Tests](https://github.com/arc-cloud-innovations/arc-cloud-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/arc-cloud-innovations/arc-cloud-cli/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/arc-cloud.svg)](https://pypi.org/project/arc-cloud/)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **ARC CLOUD CLI** is an extensible, local-first **Software Engineering Health Platform**. It provides AST-level static analysis, 10 specialized analysis engines, McCabe cyclomatic complexity profiling, automated risk assessment, engineering health scoring (0-100), AI-assisted remediation, baseline trend verification, and CI/CD quality gates with SARIF/JSON/HTML reporting.

---

## 10 Specialized Analysis Engines

| Engine | Command | Focus & Capabilities |
|---|---|---|
| **Code Quality** | `arc scan` | McCabe cyclomatic complexity (ARC001), size & structure (ARC002, ARC003, ARC006, ARC007, ARC011), duplicate code blocks (ARC004) |
| **Reliability** | `arc reliability` | Suppressed broad exceptions (`ARC-REL-001`), unclosed file descriptors without context managers (`ARC-REL-002`) |
| **Security (SAST)** | `arc security` | SQL injection (`ARC-SEC-002`), command injection `shell=True` (`ARC-SEC-003`), unsafe eval/exec (`ARC-SEC-005`), weak crypto MD5/SHA1 (`ARC-SEC-007`), cleartext HTTP (`ARC-SEC-008`) |
| **Secrets Engine** | `arc secrets` | Safe entropy & pattern scanning for AWS keys, GitHub PATs, private keys, and API credentials (strictly masked in outputs) |
| **Dependencies** | `arc deps` | Manifest analysis (package.json, requirements.txt, pubspec.yaml), wildcard pinning risks (`ARC-DEP-001`), honest vulnerability telemetry |
| **Architecture** | `arc architecture` | Modularity extraction, circular dependency detection (`ARC-ARCH-001`), layer boundary violations |
| **Technical Debt** | `arc debt` | Remediation hour estimation across complexity, security, architecture, testing, and duplication |
| **Testing** | `arc test` | Test-to-source ratios, test framework detection, critical untested core modules (`ARC-TEST-001`), telemetry coverage inspection |
| **Performance** | `arc performance` | Algorithmic complexity hotspots ($O(n^3)+$ nested loops `ARC-PERF-001`), regex compilation in tight loops (`ARC-PERF-002`) |
| **AI Risk** | `arc ai-risk` | Composite observable engineering risk assessment and defect probability |

---

## Privacy & Security Guarantee

```text
ARC CLOUD CLI performs project scanning locally.
Your source code is not uploaded to ARC CLOUD during local scanning.
```

- **100% Offline & Local-First**: Scanning runs entirely on your local machine without sending your code to any cloud server.
- **Zero Code Execution**: Manifests and code files are statically inspected. The scanner never executes project code or runs arbitrary package managers.
- **Secret Protection**: Detected secrets are always securely masked (`api...xyz`) and never printed raw.
- **No Mandatory AI / LLM Requirement**: Deterministic static analysis by default, with optional local AI enhancements.

---

## Installation

### Recommended: `pipx` (Globally Available)
Install once globally and run from any project directory:
```bash
pipx install arc-cloud
```
Or directly from GitHub:
```bash
pipx install git+https://github.com/arc-cloud-innovations/arc-cloud-cli.git
```

### Standard `pip`
```bash
pip install arc-cloud
```

### Development Installation
```bash
git clone https://github.com/arc-cloud-innovations/arc-cloud-cli.git
cd arc-cloud-cli
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Complete CLI Command Reference

### Core Platform Commands

| Command | Description |
|---|---|
| `arc scan [PATH]` | Run full 10-engine engineering health scan |
| `arc report [PATH]` | Export engineering health report (`terminal`, `json`, `sarif`, `html`) |
| `arc ci [PATH]` | Automated CI/CD quality gate with strict exit codes and SARIF export |
| `arc init [PATH]` | Initialize `.arccloud.yml` project configuration |
| `arc version` | Display platform architecture and active engine matrix |

### AI-Assisted Diagnosis & Remediation

| Command | Description |
|---|---|
| `arc explain <FINDING_OR_RULE_ID>` | Root-cause analysis, side effects, before/after code, and verification test |
| `arc fix <FINDING_ID>` | Generate and apply an automated fix patch with automatic `.bak` backup and re-scan |
| `arc plan [PATH]` | Sprint-ready prioritized engineering remediation plan (P0, P1, P2) |
| `arc review [PATH]` | Pre-commit AI code review of uncommitted git changes to prevent regressions |
| `arc verify [PATH]` | Compare current scan against baseline (`.arc/baseline.json`) and track delta |

### Targeted Engine Subcommands

| Command | Description |
|---|---|
| `arc reliability [PATH]` | Dedicated reliability, exception handling, and resource leak scan |
| `arc security [PATH]` | Dedicated SAST security vulnerability scan |
| `arc secrets [PATH]` | Dedicated secrets, credentials, and token scanner |
| `arc deps [PATH]` | Dedicated dependency and manifest analysis |
| `arc architecture [PATH]` | Dedicated circular dependency and layer violation scan |
| `arc debt [PATH]` | Dedicated technical debt and remediation hour calculation |
| `arc test [PATH]` | Dedicated testing intelligence and coverage audit |
| `arc performance [PATH]` | Dedicated algorithmic complexity and performance audit |
| `arc ai-risk [PATH]` | Dedicated composite risk evaluation |

---

## Usage Examples

### 1. Run a Full Engineering Health Scan
```bash
arc scan
```
With legacy Software Blueprint / X-Ray mode:
```bash
arc scan --blueprint
```

### 2. Generate Local Responsive HTML Report
```bash
arc scan --format html -o health_report.html
```

### 3. CI/CD Quality Gate
Integrate directly in GitHub Actions, GitLab CI, or Jenkins:
```bash
arc ci --fail-on high --min-health 80 --max-debt-hours 20
```
Exit Codes:
- `0`: Quality gate PASSED
- `1`: Quality gate FAILED (findings exceeded threshold, health below minimum)
- `2`: Configuration or usage error
- `3`: Engine or scan runtime error

Automatically emits `arc-results.sarif` compatible with GitHub Code Scanning and updates `$GITHUB_STEP_SUMMARY`.

### 4. AI-Assisted Explanation and Automated Fix
Explain any finding or rule:
```bash
arc explain ARC-SEC-002
arc explain arc-f-12345
```

Generate automated patch, create `.bak` backup, apply fix, and re-scan:
```bash
arc fix arc-f-12345 --dry-run
arc fix arc-f-12345 -y
```

### 5. Sprint-Ready Remediation Plan
```bash
arc plan
```
Outputs prioritized work breakdown:
- **P0 Immediate**: Critical security and hardcoded secrets
- **P1 Short-Term**: High reliability and architecture violations
- **P2 Long-Term**: Medium debt, testing, and performance refactoring

### 6. Baseline Verification & Regression Tracking
Track health improvements over time:
```bash
arc verify
arc verify --update-baseline
```
Reports new findings (`+N`), resolved findings (`-N`), and overall health score delta (`+X.X IMPROVED`).

---

## Configuration (`.arccloud.yml`)

```yaml
version: 1
project_name: "my-service"

scan:
  max_files: 20000
  max_depth: 20
  exclude:
    - "build/"
    - "dist/"
    - "node_modules/"
    - ".venv/"

rules:
  ARC001:
    enabled: true
    severity: "high"
    max_complexity: 10
  ARC-SEC-002:
    enabled: true
    severity: "critical"

reporting:
  format: "terminal"
  fail_on: "high"
```

---

## License

MIT License. Copyright (c) 2026 ARC CLOUD Innovations.
