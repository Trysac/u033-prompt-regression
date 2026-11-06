# Standard-library-only run comparison with escaped, fenced markdown reports

Status: accepted (generated, pending human review)

## Context

Reviewers need to see which dataset cases answer differently after a prompt change. Recorded outputs are untrusted text that ends up in pull request comments, where GitHub renders inline HTML and markdown, and the inputs can be arbitrarily large or malformed.

## Decision

Implement the tool with the Python standard library only. Runs are loaded from JSONL with explicit byte and line limits and strict validation (finite numeric scores, no NaN or Infinity, no duplicate ids) and a single typed RegressionError with stable codes. Outputs are normalised by a frozen Normalizer, compared by id with difflib unified diffs (skipped for very long outputs), and rendered either as JSON or as markdown in which every value outside a code fence is HTML-escaped and every diff is wrapped in a fence longer than any backtick run it contains. Core modules are named comparison and report so they do not shadow the public functions compare and render.

## Consequences

The library has no runtime dependencies and deterministic behaviour that is easy to test. Numbers keep Python JSON types, so 1 and 1.0 are reported as changed on purpose. Very long outputs get a status but no diff. Reports stay safe in pull request comments at the price of escaping some characters in case ids. Embedding similarity, running prompts and HTML reports are out of scope.
