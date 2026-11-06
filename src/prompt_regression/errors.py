"""Typed errors of prompt-regression."""

from __future__ import annotations

from typing import Final, Literal

ErrorCode = Literal["input_invalid", "input_too_large", "duplicate_case_id"]

MAX_MESSAGE_CHARS: Final = 200


def clip(text: str, limit: int = MAX_MESSAGE_CHARS) -> str:
    """Return ``text`` shortened to at most ``limit`` characters."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class RegressionError(Exception):
    """Base error of the library.

    Attributes:
        code: Stable machine-readable error code.
        path: File the error refers to, if any.
        line: 1-based line number the error refers to, if any.
        message: Human readable reason, at most 200 characters.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        path: str | None = None,
        line: int | None = None,
    ) -> None:
        self.code: ErrorCode = code
        self.path = path
        self.line = line
        self.message = clip(message)
        super().__init__(self.message)
