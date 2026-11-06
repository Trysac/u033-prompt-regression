# prompt-regression

[![PyPI version](https://img.shields.io/pypi/v/trysac-prompt-regression)](https://pypi.org/project/trysac-prompt-regression/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-prompt-regression)](LICENSE)
[![CI](https://github.com/Trysac/u033-prompt-regression/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u033-prompt-regression/actions/workflows/ci.yml)

Compare recorded outputs of two prompt versions over the same dataset and report unchanged, changed, improved, regressed, added and removed cases

## Problem

When a prompt changes, reviewers need to see which dataset cases now answer differently, not just an aggregate score. Manually diffing two JSONL runs is tedious and noisy because of whitespace and key order. This utility aligns two recorded runs by case id, normalizes both outputs and reports the meaningful differences in a form that can be pasted into a pull request.

## Install

```sh
pip install trysac-prompt-regression
# or
uv add trysac-prompt-regression
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from pathlib import Path
from prompt_regression import compare, load_run, render

before = load_run(Path("before.jsonl"))
after = load_run(Path("after.jsonl"))
diffs = compare(before, after)
print(render(diffs, "markdown"))
```

Command line: `python -m prompt_regression BEFORE.jsonl AFTER.jsonl [--fail-on regressed]`.

## Public API

- `load_run(path, max_bytes=50_000_000, max_line_bytes=1_048_576) -> dict[str, RunRecord]`: reads JSONL lines with `id` (string), `output` (string) and optional `score` (finite JSON number, not boolean). `NaN` and `Infinity` are rejected. Duplicate ids are rejected.
- `RunRecord(case_id, output, score=None)`: one recorded output.
- `Normalizer(strip=True, casefold=False, json_canonical=False).apply(text) -> str`: CRLF to LF; with `strip`, trailing spaces per line and surrounding whitespace removed; with `casefold`, case-folded; with `json_canonical`, a text that is one JSON document is re-serialised with sorted keys and compact separators. `1` and `1.0` remain different.
- `compare(before, after, normalizer=Normalizer(), tolerance=0.0) -> list[CaseDiff]`: one `CaseDiff` per id in the union of both runs, sorted by id. Statuses: `unchanged`, `changed`, `improved`, `regressed`, `added`, `removed`. Scores decide between improved and regressed only when both runs have a score and the delta exceeds `tolerance`.
- `render(diffs, fmt, max_diff_lines=40) -> str`: `fmt` is `"markdown"` or `"json"`. Markdown escapes case ids and fences diffs with a backtick run longer than any inside them.
- `RegressionError(code, message, path=None, line=None)`: codes `input_invalid`, `input_too_large`, `duplicate_case_id`. Messages are at most 200 characters.
- Limits: `Normalizer.apply` rejects texts over 10,000,000 characters; diffs are omitted when an output exceeds 100,000 characters.
- CLI exit codes: 0 pass, 1 the `--fail-on` condition is met, 2 usage or input error.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
