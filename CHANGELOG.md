# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `prompt_regression` to compare two recorded JSONL prompt runs by case id (`load_run`, `Normalizer`, `compare`, `render`) with a `python -m prompt_regression` CLI that reports unchanged, changed, improved, regressed, added and removed cases as escaped markdown or JSON.
- Initial project structure from the factory utility template.
