# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-07

Major upgrade from code scanner to comprehensive Software Engineering Health Platform.

- **10 Specialized Analysis Engines**:
  - `Code Quality`: McCabe cyclomatic complexity (`ARC001`), size and structure rules (`ARC002`, `ARC003`, `ARC006`, `ARC007`, `ARC011`), and duplicate code block detection (`ARC004`).
  - `Reliability`: Detection of suppressed broad exceptions (`ARC-REL-001`) and unclosed file descriptor leaks (`ARC-REL-002`).
  - `Security (SAST)`: SQL injection (`ARC-SEC-002`), command injection `shell=True` (`ARC-SEC-003`), unsafe dynamic execution (`ARC-SEC-005`), broken cryptographic hashes (`ARC-SEC-007`), and cleartext HTTP endpoints (`ARC-SEC-008`).
  - `Secrets Engine`: High-entropy and credential detection (AWS keys, GitHub PATs, private keys) with strict automated masking (`api...xyz`).
  - `Dependencies Engine`: Manifest parsing (`package.json`, `requirements.txt`, `pubspec.yaml`), wildcard version risks (`ARC-DEP-001`), and honest vulnerability metrics.
  - `Architecture Engine`: Package modularity, circular dependency cycle detection (`ARC-ARCH-001`), and layer boundary violations.
  - `Technical Debt Engine`: Remediation hour estimation by category with prioritized action plans.
  - `Testing Intelligence Engine`: Test-to-source ratio, test framework detection, critical untested core modules (`ARC-TEST-001`), and honest coverage reporting.
  - `Performance Engine`: High algorithmic complexity hotspots ($O(n^3)+$ nested loops `ARC-PERF-001`) and regex compilation inside tight loops (`ARC-PERF-002`).
  - `AI Risk Engine`: Composite observable engineering risk assessment.
- **Dedicated Engine Commands**:
  - Added `arc reliability`, `arc security`, `arc secrets`, `arc deps`, `arc architecture`, `arc debt`, `arc test`, `arc performance`, and `arc ai-risk`.
- **AI-Assisted Diagnosis & Remediation**:
  - `arc explain <FINDING_OR_RULE_ID>`: Root cause explanation, why it matters, risk if not fixed, step-by-step remediation guide, before/after code, side effects, and verification tests.
  - `arc fix <FINDING_ID>`: Automated patch generation, `.bak` file backup, patch application, and verification re-scan.
  - `arc plan`: Sprint-ready prioritized remediation checklist (P0, P1, P2) with estimated hours.
  - `arc review`: Pre-commit git diff code review preventing regressions before commit.
  - `arc verify`: Baseline tracking (`.arc/baseline.json`) with new, fixed, and remaining findings diff and health score trend.
- **Local Responsive HTML Reporting**:
  - `arc scan --format html`: Local, responsive, zero-dependency HTML reports with search, filter controls, expandable findings, and print stylesheet.
- **CI/CD Quality Gate**:
  - `arc ci`: Automated CI/CD execution with `--fail-on`, `--min-health`, `--max-debt-hours`, strict exit codes (0, 1, 2, 3), SARIF export, and GitHub Actions step summary integration.
- **Zero Regression**:
  - Preserved backward-compatible `arc scan --blueprint`, `arc init`, and legacy blueprint schemas.
  - Test suite expanded from 66 to 81 unit & integration tests.

## [0.1.0] - 2026-09-04

Initial public release of ARC CLOUD CLI.

- **Local Software X-Ray Scanning**: Deterministic static analysis without executing project code or requiring an LLM/cloud account.
- **Language Detection**: Extension- and manifest-based detection for Dart, Python, JavaScript, TypeScript, Java, Kotlin, Swift, C#, C++, Go, Rust, PHP, and Ruby with file counts and percentage metrics.
- **Modular Framework Detectors**: Independent detectors for Flutter, React, Next.js, Node.js, FastAPI, Django, Spring Boot, and .NET.
- **Target Platform Detection**: Automated detection for Android, iOS, Web, Windows, macOS, and Linux.
- **Safe Dependency Extraction**: Static parsing for `pubspec.yaml`, `package.json`, `requirements.txt`, `pyproject.toml`, `Pipfile`, `pom.xml`, `build.gradle`, and `*.csproj`.
- **Configuration & Structure Analysis**: Categorizes directories into source, tests, assets, platforms, configuration, and documentation; catalogs key project manifests.
- **Software Blueprint Schema v1.0**: Validated Pydantic models with schema versioning.
- **Rich Terminal UI**: Polished terminal presentation powered by Rich.
- **Flexible Output Modes**: Raw JSON output (`arc scan --json`) and direct file export (`arc scan --output blueprint.json`).
- **Security & Limits**: Hardened path traversal protection, symlink escape isolation, sensitive/`.env` file blocking, and safe traversal limits.
- **Global Executable**: Installs globally as `arc` via `pipx` or standard `pip`.
