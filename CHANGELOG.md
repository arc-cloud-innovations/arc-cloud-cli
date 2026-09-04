# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
