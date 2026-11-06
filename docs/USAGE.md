# Usage

`prompt-regression` aligns two recorded JSONL runs by case id, normalises the outputs and reports
which cases are `unchanged`, `changed`, `improved`, `regressed`, `added` or `removed`.

## Input format

One JSON object per line: `id` (string), `output` (string) and an optional `score` (finite JSON
number; booleans, strings, `NaN` and `Infinity` are rejected). Blank lines are ignored. Duplicate
ids, files above 50 MB and lines above 1 MiB are rejected with a typed `RegressionError`.

## Command line

```text
python -m prompt_regression BEFORE.jsonl AFTER.jsonl [--format markdown|json] [--casefold]
    [--json-canonical] [--no-strip] [--tolerance X] [--fail-on regressed|changed|never]
    [--max-diff-lines N]
```

Exit codes: `0` pass, `1` the `--fail-on` condition is met, `2` usage or input error (the message on
stderr has the form `path:line: reason`).

## Normalisation

CRLF becomes LF; with strip (default) trailing spaces are trimmed per line and the whole text is
stripped; then optional casefolding; then, with `--json-canonical`, a text that is entirely one JSON
document is re-serialised with sorted keys and compact separators. Numbers keep Python's JSON
types, so `1` and `1.0`, or `0.0` and `-0.0`, are deliberately reported as `changed`.

## Status rules

Equal normalised outputs are `unchanged`, even when scores differ. Otherwise, when both runs carry
a score, `delta = after - before` decides: `improved` if `delta > tolerance`, `regressed` if
`delta < -tolerance`, else `changed`. Without both scores the status is `changed`.

## Safety of the report

Markdown reports are meant for pull request comments, where inline HTML is rendered. Case ids are
escaped (`&`, `<`, `>` as entities and `|` as `\|`, line breaks replaced by spaces) and every diff
sits in a code fence longer than any backtick run it contains, so recorded outputs cannot close the
block or inject markup. Diffs are skipped for outputs above 100 000 characters.
