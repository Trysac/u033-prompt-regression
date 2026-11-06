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
| Tokens (input / output) | 258361 / 67123 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.4801 |

## Factory run u033 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2568 | 60903 | 0 | 4246 | 0.3075 |
| fix-1 | claude-sonnet-5-5 | no | 4 | 610 | 6412 | 24735 | 0.0246 |
| fix-2 | claude-sonnet-5-5 | no | 4 | 478 | 7631 | 26230 | 0.0265 |
| fix-3 | claude-sonnet-5-5 | no | 8 | 829 | 6972 | 55395 | 0.0313 |
| fix-4 | claude-sonnet-5-5 | no | 4 | 299 | 5781 | 24502 | 0.0199 |
| docs | claude-haiku-5-5 | no | 120665 | 4004 | 0 | 0 | 0.0703 |

Total: $0.4801. Prices: Anthropic list prices.
