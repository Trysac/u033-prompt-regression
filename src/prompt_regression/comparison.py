"""Alignment and comparison of two recorded runs."""

from __future__ import annotations

import difflib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

from prompt_regression.errors import RegressionError
from prompt_regression.loader import RunRecord
from prompt_regression.normalizer import Normalizer

Status = Literal["unchanged", "changed", "improved", "regressed", "added", "removed"]

STATUSES: Final[tuple[Status, ...]] = (
    "unchanged",
    "changed",
    "improved",
    "regressed",
    "added",
    "removed",
)
MAX_DIFF_CHARS: Final = 100_000
DIFF_OMITTED: Final = "diff omitted: output too long"
_DEFAULT_NORMALIZER: Final = Normalizer()


@dataclass(frozen=True)
class CaseDiff:
    """Comparison result for one case id.

    Attributes:
        case_id: Identifier of the case.
        status: Outcome of the comparison.
        before: Raw output of the first run, or None when absent.
        after: Raw output of the second run, or None when absent.
        score_delta: ``after - before`` score for changed outputs with both scores.
        diff: Unified diff lines over the normalised outputs.
    """

    case_id: str
    status: Status
    before: str | None
    after: str | None
    score_delta: float | None
    diff: tuple[str, ...]


def check_tolerance(tolerance: float) -> None:
    """Raise ``RegressionError`` unless ``tolerance`` is a finite number >= 0."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise RegressionError("input_invalid", "tolerance must be a finite number >= 0")


def _lines(text: str) -> list[str]:
    return text.split("\n") if text else []


def _unified(raw_old: str, raw_new: str, norm_old: str, norm_new: str) -> tuple[str, ...]:
    if len(raw_old) > MAX_DIFF_CHARS or len(raw_new) > MAX_DIFF_CHARS:
        return (DIFF_OMITTED,)
    lines = difflib.unified_diff(
        _lines(norm_old),
        _lines(norm_new),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return tuple(lines)


def _compare_pair(
    case_id: str, old: RunRecord, new: RunRecord, normalizer: Normalizer, tolerance: float
) -> CaseDiff:
    norm_old = normalizer.apply(old.output)
    norm_new = normalizer.apply(new.output)
    if norm_old == norm_new:
        return CaseDiff(case_id, "unchanged", old.output, new.output, None, ())
    status: Status = "changed"
    delta: float | None = None
    if old.score is not None and new.score is not None:
        delta = new.score - old.score
        if delta > tolerance:
            status = "improved"
        elif delta < -tolerance:
            status = "regressed"
    diff = _unified(old.output, new.output, norm_old, norm_new)
    return CaseDiff(case_id, status, old.output, new.output, delta, diff)


def _added(case_id: str, new: RunRecord, normalizer: Normalizer) -> CaseDiff:
    diff = _unified("", new.output, "", normalizer.apply(new.output))
    return CaseDiff(case_id, "added", None, new.output, None, diff)


def _removed(case_id: str, old: RunRecord, normalizer: Normalizer) -> CaseDiff:
    diff = _unified(old.output, "", normalizer.apply(old.output), "")
    return CaseDiff(case_id, "removed", old.output, None, None, diff)


def compare(
    before: Mapping[str, RunRecord],
    after: Mapping[str, RunRecord],
    normalizer: Normalizer = _DEFAULT_NORMALIZER,
    tolerance: float = 0.0,
) -> list[CaseDiff]:
    """Compare two runs aligned by case id.

    Returns one ``CaseDiff`` per id in the union of both runs, sorted by id. Equal normalised
    outputs are ``unchanged``. Otherwise, when both runs have a score, the delta decides
    between ``improved`` (delta > tolerance), ``regressed`` (delta < -tolerance) and
    ``changed``; without both scores the status is ``changed``.

    Raises:
        RegressionError: ``input_invalid`` when ``tolerance`` is negative or not finite, or
            ``input_too_large`` when an output exceeds the normaliser limit.
    """
    check_tolerance(tolerance)
    diffs: list[CaseDiff] = []
    for case_id in sorted(before.keys() | after.keys()):
        old = before.get(case_id)
        new = after.get(case_id)
        if old is not None and new is not None:
            diffs.append(_compare_pair(case_id, old, new, normalizer, tolerance))
        elif new is not None:
            diffs.append(_added(case_id, new, normalizer))
        elif old is not None:
            diffs.append(_removed(case_id, old, normalizer))
    return diffs
