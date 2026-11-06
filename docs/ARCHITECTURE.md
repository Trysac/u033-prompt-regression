# Architecture

## Purpose

`trysac-prompt-regression` is a small, dependency-free Python package that compares recorded outputs of two prompt versions over the same dataset and reports unchanged, changed, improved, regressed, added and removed cases.

## Shape

```text
caller code / CLI --> prompt_regression
    load_run (JSONL reader, bounded)
    Normalizer (text normalisation)
    compare (alignment by case id, status)
    render (markdown or JSON)
```

- **Modules**: `loader.py` (reads JSONL), `normalizer.py`, `comparison.py` (alignment and `compare`), `report.py` (`render`), `errors.py` (`RegressionError`), `__main__.py` (command line).
- **Public API**: the names listed in `__all__` of `src/prompt_regression/__init__.py`. Anything else is internal.
- **Errors**: invalid input raises `RegressionError` with a stable `code`. The library itself does not print or exit; the CLI writes to stderr and returns exit code 2.
- **I/O**: only `load_run` reads files; it is the only function that touches the file system.

## Quality contract

The gates are described in [TESTING.md](TESTING.md).

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
