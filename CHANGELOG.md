# Changelog

All notable changes to PlanWeaver will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Deprecated

### Removed

### Security

---

## Recent Changes (2026-02)

### 2026-02-27

**Added**
- Plan Optimizer feature with variant generation and multi-model rating
- Model selection UI for planner and executor models
- OptimizerStage, ComparisonPanel, and PlanCard frontend components
- Frontend test infrastructure with vitest and playwright

**Fixed**
- Enforced strict session model overrides
- Corrected relative import paths in optimizer router
- Fixed failing optimizer tests

**Documentation**
- Added comprehensive Plan Optimizer feature guide
- Updated architecture.md with Plan Optimizer components
- Added Plan Optimizer implementation summary

### 2026-02-26

**Research**
- Planning enhancement research document
- Planning frameworks research and analysis

### 2026-02-18

**Documentation**
- External context feature guide

### 2026-02-16

**Documentation**
- Project documentation updates

---

## Version History

### Key Features by Release

#### Current Development Version

- **Plan Optimizer**: Generate AI-optimized plan variants with multi-model rating
- **External Context**: Enhance planning with GitHub repos, web search, and file uploads
- **Model Selection**: UI for selecting planner and executor models per session
- **Frontend Testing**: Comprehensive test coverage with vitest and playwright
- **Interactive Planning**: Clarifying questions and strawman proposals
- **DAG Execution**: Dependency-aware step execution with retries

#### Recent Model Changes

- **Default Planner**: gemini-2.5-flash (price-performance optimized)
- **Default Executor**: gemini-3-flash (latest balanced model)
- **Previous Defaults**: DeepSeek V3 (planner), Claude 3.5 Sonnet (executor)

---

## Breaking Changes

### Session Model Overrides (2026-02-27)

Session model overrides are now strictly enforced. Previously, step-level `assigned_model` values could override session-level settings. Now session-level `planner_model` and `executor_model` take precedence.

**Migration**: If you were relying on step-level model assignments, update your code to use session-level model overrides.

---

## Upcoming Features

See GitHub issues and project board for planned features and enhancements.

---

## Contributors

Thanks to everyone who has contributed to PlanWeaver!

For a full list of contributors, see [contributors.md](CONTRIBUTORS.md) (if available) or check the GitHub repository.
