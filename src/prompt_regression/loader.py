"""Loading of recorded runs from JSONL files."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NoReturn

from prompt_regression.errors import RegressionError, clip

logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES: Final = 50_000_000
DEFAULT_MAX_LINE_BYTES: Final = 1_048_576


@dataclass(frozen=True)
class RunRecord:
    """One recorded model output for a dataset case.

    Attributes:
        case_id: Identifier of the dataset case.
        output: Recorded output text.
        score: Optional finite score of the output.
    """

    case_id: str
    output: str
    score: float | None = None


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"unsupported JSON constant {clip(name, 20)}")


def _invalid(message: str, path: str, line: int | None) -> NoReturn:
    raise RegressionError("input_invalid", message, path, line)


def _check_text(value: str, what: str, path: str, line: int) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _invalid(f"{what} contains an unpaired surrogate", path, line)


def _parse_score(raw: Any, path: str, line: int) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        _invalid("score must be a JSON number", path, line)
    try:
        score = float(raw)
    except OverflowError:
        _invalid("score is out of range", path, line)
    if not math.isfinite(score):
        _invalid("score must be finite", path, line)
    return score


def _parse_line(content: bytes, path: str, line: int) -> RunRecord | None:
    if not content.strip():
        return None
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        _invalid("line is not valid UTF-8", path, line)
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        _invalid(f"invalid JSON: {clip(str(exc), 100)}", path, line)
    if not isinstance(data, dict):
        _invalid("line must be a JSON object", path, line)
    case_id = data.get("id")
    output = data.get("output")
    if not isinstance(case_id, str):
        _invalid("id must be a string", path, line)
    if not isinstance(output, str):
        _invalid("output must be a string", path, line)
    _check_text(case_id, "id", path, line)
    _check_text(output, "output", path, line)
    return RunRecord(case_id, output, _parse_score(data.get("score"), path, line))


def _read_lines(
    path: Path, spath: str, max_bytes: int, max_line_bytes: int
) -> Iterator[tuple[int, bytes]]:
    total = 0
    line_no = 0
    try:
        with path.open("rb") as handle:
            while raw := handle.readline(max_line_bytes + 2):
                line_no += 1
                total += len(raw)
                if total > max_bytes:
                    message = f"file exceeds {max_bytes} bytes"
                    raise RegressionError("input_too_large", message, spath, line_no)
                content = raw.removesuffix(b"\n").removesuffix(b"\r")
                if len(content) > max_line_bytes:
                    message = f"line exceeds {max_line_bytes} bytes"
                    raise RegressionError("input_too_large", message, spath, line_no)
                yield line_no, content
    except OSError as exc:
        _invalid(f"cannot read file: {exc.strerror or type(exc).__name__}", spath, None)


def load_run(
    path: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
) -> dict[str, RunRecord]:
    """Read a JSONL run file into a mapping from case id to record.

    Every non-blank line is a JSON object with ``id`` (str), ``output`` (str) and an optional
    ``score`` (finite JSON number, not a boolean). ``NaN`` and ``Infinity`` are rejected.

    Args:
        path: File to read.
        max_bytes: Maximum file size in bytes.
        max_line_bytes: Maximum size of one line in bytes, excluding the line terminator.

    Raises:
        RegressionError: ``input_too_large`` when a limit is exceeded, ``input_invalid`` for
            unreadable or malformed input and ``duplicate_case_id`` for a repeated id.
    """
    spath = str(path)
    if max_bytes < 0 or max_line_bytes < 0:
        _invalid("size limits must not be negative", spath, None)
    try:
        size = path.stat().st_size
    except OSError as exc:
        _invalid(f"cannot read file: {exc.strerror or type(exc).__name__}", spath, None)
    if size > max_bytes:
        raise RegressionError("input_too_large", f"file exceeds {max_bytes} bytes", spath)
    records: dict[str, RunRecord] = {}
    for line_no, content in _read_lines(path, spath, max_bytes, max_line_bytes):
        record = _parse_line(content, spath, line_no)
        if record is None:
            continue
        if record.case_id in records:
            message = f"duplicate case id {clip(repr(record.case_id), 80)}"
            raise RegressionError("duplicate_case_id", message, spath, line_no)
        records[record.case_id] = record
    logger.debug("loaded %d records", len(records))
    return records
