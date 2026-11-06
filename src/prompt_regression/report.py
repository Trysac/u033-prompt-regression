"""Rendering of comparison results as markdown or JSON."""

from __future__ import annotations

import dataclasses
import json
import re
from collections import Counter
from collections.abc import Sequence
from typing import Final, Literal

from prompt_regression.comparison import STATUSES, CaseDiff
from prompt_regression.errors import RegressionError, clip

Format = Literal["markdown", "json"]

_BACKTICK_RUN: Final = re.compile(r"`+")
_ESCAPES: Final = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("|", "\\|"))


def _escape(text: str) -> str:
    result = " ".join(text.splitlines())
    for char, entity in _ESCAPES:
        result = result.replace(char, entity)
    return result


def _details(diff: CaseDiff, max_lines: int) -> list[str]:
    shown = list(diff.diff[:max_lines])
    hidden = len(diff.diff) - len(shown)
    if hidden > 0:
        shown.append(f"... {hidden} more lines")
    longest = max((len(run) for run in _BACKTICK_RUN.findall("\n".join(shown))), default=0)
    fence = "`" * max(3, longest + 1)
    return [
        f"<details><summary>{_escape(diff.case_id)} ({diff.status})</summary>",
        "",
        f"{fence}diff",
        *shown,
        fence,
        "</details>",
    ]


def _render_markdown(diffs: Sequence[CaseDiff], max_diff_lines: int) -> str:
    counts = Counter(d.status for d in diffs)
    lines = ["## Prompt regression", "", "| status | count |", "| --- | --- |"]
    lines.extend(f"| {status} | {counts[status]} |" for status in STATUSES)
    for diff in sorted(diffs, key=lambda d: d.case_id):
        if diff.status != "unchanged":
            lines.append("")
            lines.extend(_details(diff, max_diff_lines))
    return "\n".join(lines)


def render(diffs: Sequence[CaseDiff], fmt: Format, max_diff_lines: int = 40) -> str:
    """Render ``diffs`` as a markdown report or as JSON.

    Markdown output is safe to paste into a pull request comment: case ids are HTML-escaped
    and diffs sit inside a code fence longer than any backtick run they contain.

    Raises:
        RegressionError: ``input_invalid`` for an unknown format or a negative line limit.
    """
    if max_diff_lines < 0:
        raise RegressionError("input_invalid", "max_diff_lines must not be negative")
    if fmt == "json":
        return json.dumps([dataclasses.asdict(d) for d in diffs], sort_keys=True, indent=2)
    if fmt == "markdown":
        return _render_markdown(diffs, max_diff_lines)
    raise RegressionError("input_invalid", f"unknown format {clip(repr(fmt), 50)}")
