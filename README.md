# ARC CLOUD — Software Engineering Health Platform CLI

[![CI Tests](https://github.com/arc-cloud-innovations/arc-cloud-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/arc-cloud-innovations/arc-cloud-cli/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/arc-cloud.svg)](https://pypi.org/project/arc-cloud/)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **ARC CLOUD CLI** is an extensible, local-first **Software Engineering Health Platform**. It provides AST-level static analysis, McCabe cyclomatic complexity profiling, automated risk assessment, engineering health scoring (0-100), and CI/CD ready SARIF/JSON reporting.

---

## Key Capabilities

- **Project Intelligence**: Fast, recursive file indexing respecting `.gitignore`, excluding vendor/build folders (`node_modules`, `.venv`, `.dart_tool`, `build`), and counting total, source, and test lines of code.
- **AST Parsing Layer**: Python AST visitor calculating exact McCabe cyclomatic complexity across functions and methods.
- **Rule Engine**: Deterministic rules including `ARC001` (Excessive Function Complexity) with clear remediation guidance.
- **Centralized Severity & Risk Engine**: Uniform severity weighting (CRITICAL: 10, HIGH: 5, MEDIUM: 2, LOW: 1, INFO: 0) and holistic risk levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE`).
- **Health Scoring Engine**: Transparent 0-100 overall health score and letter grades (A-F), with explicit unanalyzed status for unconfigured dimensions (no fake numbers).
- **Multi-Format Reporting**: Rich terminal dashboard, standard SARIF v2.1.0 (GitHub Code Scanning compatible), and clean JSON.
- **CI/CD Failure Gates**: Exit codes (0 = pass, 1 = issues exceed threshold, 2 = config error, 3 = scan error) and `--fail-on` options.

---

## Privacy & Security Guarantee

```text
ARC CLOUD CLI performs project scanning locally.
Your source code is not uploaded to ARC CLOUD during local scanning.
```

- **100% Offline & Local**: Scanning runs entirely on your local machine without sending your code to any cloud server or LLM API.
- **Zero Code Execution**: Manifests and code files are statically inspected. The scanner never executes project code or runs package managers.
- **Secret Protection**: Files matching `.env`, `.env.*`, `credentials.json`, `id_rsa`, `*.key`, and secret patterns are never read or indexed.
- **No AI / LLM Requirement**: Pure deterministic static analysis.

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

## CLI Commands Overview

| Command | Description |
|---|---|
| `arc init` | Generate default `.arccloud.yml` project configuration |
| `arc scan` | Analyze software project and evaluate engineering health |
| `arc explain [RULE_ID]` | Show in-depth explanation and remediation guidance for a rule |
| `arc report` | Generate and export health reports in terminal, json, or sarif format |
| `arc version` | Display platform architecture and engine availability |

---

## Usage Guide

### 1. Initialize Configuration (`arc init`)
Create an `.arccloud.yml` file in your repository:
```bash
arc init
```

### 2. Run Health Scan (`arc scan`)
Scan current directory:
```bash
arc scan
```

Scan another directory with JSON output:
```bash
arc scan ~/Projects/my_backend --format json
```

Export SARIF report for GitHub Code Scanning:
```bash
arc scan . --format sarif --output results.sarif
```

Fail CI/CD pipeline on High or Critical severity findings:
```bash
arc scan . --fail-on high
```

### 3. Explain Rules (`arc explain`)
List all registered static analysis rules:
```bash
arc explain
```

Get detailed explanation, why it matters, anti-patterns, and fixes:
```bash
arc explain ARC001
```

### 4. Generate Reports (`arc report`)
```bash
arc report --format json --output report.json
arc report --format sarif --output report.sarif
```

### 5. Check Engine Status (`arc version`)
```bash
arc version
```

---

## Configuration (`.arccloud.yml`)

ARC CLOUD can be configured per repository with `.arccloud.yml`:

```yaml
# ARC CLOUD Project Configuration
project:
  name: my-service

scan:
  exclude:
    - .git
    - node_modules
    - .venv
    - venv
    - build
    - dist
    - .dart_tool
    - .gradle
    - target
    - __pycache__
  max_files: 20000
  max_depth: 20

rules:
  ARC001:
    enabled: true
    threshold: 10

output:
  format: terminal
```

---

## CI/CD Exit Codes

ARC CLOUD uses standard exit codes suitable for automated CI pipelines:

- `0`: Scan succeeded; no issues exceeded failure threshold.
- `1`: Scan completed; issues found that exceed `--fail-on` severity threshold.
- `2`: Configuration or invalid argument error.
- `3`: Runtime error during scan execution.

---

## GitHub Actions Integration

```yaml
name: ARC CLOUD Health Scan

on: [push, pull_request]

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install ARC CLOUD
        run: pip install arc-cloud

      - name: Run ARC CLOUD Scan
        run: arc scan . --format sarif --output arc-results.sarif --fail-on high

      - name: Upload SARIF report
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: arc-results.sarif
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
