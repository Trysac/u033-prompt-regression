# Security notes

## Threat model

`trysac-prompt-regression` reads local JSONL files and writes reports. It has no network access and no runtime dependencies.

### Defended

- **Oversized input**: `load_run` rejects files above `max_bytes` (default 50,000,000) and lines above `max_line_bytes` (default 1,048,576) with `input_too_large`. `Normalizer.apply` rejects texts above 10,000,000 characters.
- **Non-finite and boolean scores**: `NaN`, `Infinity`, booleans and non-numeric scores are rejected with `input_invalid`.
- **Malformed input**: invalid UTF-8, unpaired surrogates, invalid JSON and deeply nested JSON (recursion) raise `input_invalid` instead of crashing.
- **Markdown injection in pull request comments**: case ids and text outside code fences are HTML-escaped (`&`, `<`, `>`) and `|` is escaped; diffs are placed in a fence longer than any backtick run they contain.
- **Long error messages**: `RegressionError` messages are clipped to 200 characters; file content is not echoed beyond clipped excerpts.
- **Code execution**: no `eval`, `exec` or pickle; JSON is parsed with `json.loads`.

### Not defended

- Resource use below the limits: a file of up to 50 MB is read and held in memory as dictionaries; the library does not stream results.
- Diff size: diffs are shown in full up to 100,000 characters per output and truncated only in rendering by `max_diff_lines`.
- Content of the reports: the library does not redact sensitive text present in recorded outputs.
- Supply chain: the package has no runtime dependencies, but the development tools and CI actions are not audited by this project beyond Dependabot updates.

## Publishing

Releases are published to PyPI with trusted publishing (OIDC) when available, never with a long-lived token stored in the repository.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
