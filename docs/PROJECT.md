# Project record

## Objective

Compare recorded outputs of two prompt versions over the same dataset and report unchanged, changed, improved, regressed, added and removed cases, so that reviewers see which cases now answer differently. Manual diffs of JSONL runs are noisy because of whitespace and key order; the utility normalizes both sides before comparing.

## Scope

- In scope: `load_run`, `Normalizer`, `compare`, `render`, `RegressionError`, and the command line `python -m prompt_regression`.
- In scope: markdown and JSON reports; markdown output is escaped for pull request comments.
- Out of scope: embeddings similarity, running prompts against models, HTML reports.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | pending measurement |
| Hours (human) | pending measurement |
| Cost (USD) | pending measurement |
