# Testing

## Running

```sh
uv run pytest --cov=prompt_regression
```

## Tests

- `tests/test_prompt_regression.py` is the only test module. It imports the public API (`import prompt_regression`) and covers:
  - `load_run`: reading JSONL records, duplicate ids, invalid JSON, `NaN` and boolean scores, size limits (`input_too_large`);
  - `Normalizer`: stripping, casefolding and JSON canonicalisation;
  - `compare`: statuses `unchanged`, `changed`, `improved`, `regressed`, `added`, `removed` and the tolerance rule;
  - `render`: markdown table and escaping, dynamic code fences, truncation of diffs, JSON output;
  - the command line (`main`) and exit codes;
  - the package version and the `NullHandler` on the package logger.
- Tests write their inputs into pytest's `tmp_path` and do not use the network.

## Policy

- Tests assert return values, raised exceptions and their codes or messages.
- Each bug fix should start with a failing test that reproduces it.
- Tests are deterministic and independent of test order.

## Gates

`scripts/check.py` is referenced by the factory and CI as the single definition of the gates; the repository's copy is not part of the code snapshot reviewed here.
