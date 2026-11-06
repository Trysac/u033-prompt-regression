"""Command line interface: ``python -m prompt_regression BEFORE.jsonl AFTER.jsonl``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from prompt_regression.comparison import CaseDiff, check_tolerance, compare
from prompt_regression.errors import RegressionError
from prompt_regression.loader import load_run
from prompt_regression.normalizer import Normalizer
from prompt_regression.report import render


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-regression",
        description="Compare two recorded prompt runs (JSONL) aligned by case id.",
    )
    parser.add_argument("before", type=Path, help="JSONL run of the old prompt")
    parser.add_argument("after", type=Path, help="JSONL run of the new prompt")
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=("markdown", "json"),
        default="markdown",
    )
    parser.add_argument(
        "--casefold",
        action="store_true",
        help="compare case-insensitively",
    )
    parser.add_argument(
        "--json-canonical",
        action="store_true",
        help="compare JSON outputs structurally",
    )
    parser.add_argument(
        "--no-strip",
        dest="strip",
        action="store_false",
        help="keep surrounding whitespace",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help="score delta treated as noise",
    )
    parser.add_argument(
        "--fail-on",
        choices=("regressed", "changed", "never"),
        default="never",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=40,
        help="diff lines shown per case",
    )
    return parser


def _exit_code(diffs: Sequence[CaseDiff], fail_on: str) -> int:
    if fail_on == "regressed":
        return 1 if any(d.status == "regressed" for d in diffs) else 0
    if fail_on == "changed":
        return 1 if any(d.status != "unchanged" for d in diffs) else 0
    return 0


def _format_error(exc: RegressionError) -> str:
    if exc.path is None:
        return f"prompt-regression: {exc.message}"
    if exc.line is None:
        return f"{exc.path}: {exc.message}"
    return f"{exc.path}:{exc.line}: {exc.message}"


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface and return the process exit code.

    Exit codes: 0 pass, 1 the ``--fail-on`` condition is met, 2 usage or input error.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code is None:
            return 0
        return exc.code if isinstance(exc.code, int) else 2
    try:
        check_tolerance(args.tolerance)
        before = load_run(args.before)
        after = load_run(args.after)
        normalizer = Normalizer(
            strip=args.strip,
            casefold=args.casefold,
            json_canonical=args.json_canonical,
        )
        diffs = compare(before, after, normalizer, args.tolerance)
        report = render(diffs, args.fmt, args.max_diff_lines)
    except RegressionError as exc:
        sys.stderr.write(_format_error(exc) + "\n")
        return 2
    sys.stdout.write(report + "\n")
    return _exit_code(diffs, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
