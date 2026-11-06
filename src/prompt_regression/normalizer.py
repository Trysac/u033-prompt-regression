"""Text normalisation applied before two outputs are compared."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final, NoReturn

from prompt_regression.errors import RegressionError

MAX_NORMALIZE_CHARS: Final = 10_000_000


def _reject_constant(name: str) -> NoReturn:
    raise ValueError("unsupported JSON constant")


def _canonical_json(text: str) -> str:
    try:
        value = json.loads(text, parse_constant=_reject_constant)
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (ValueError, RecursionError):
        return text


@dataclass(frozen=True)
class Normalizer:
    """Configurable normalisation of an output text.

    Order of operations: CRLF to LF and, with ``strip``, trailing spaces trimmed per line and
    the whole text stripped; then ``casefold``; then, with ``json_canonical``, a text that is
    entirely one JSON document is re-serialised with sorted keys and compact separators.
    Decoded numbers keep Python's JSON types, so ``1`` and ``1.0`` (or ``0.0`` and ``-0.0``)
    stay different on purpose.
    """

    strip: bool = True
    casefold: bool = False
    json_canonical: bool = False

    def apply(self, text: str) -> str:
        """Return the normalised form of ``text``.

        Raises:
            RegressionError: ``input_too_large`` when ``text`` exceeds 10_000_000 characters.
        """
        if len(text) > MAX_NORMALIZE_CHARS:
            raise RegressionError(
                "input_too_large", f"text exceeds {MAX_NORMALIZE_CHARS} characters"
            )
        result = text.replace("\r\n", "\n")
        if self.strip:
            result = "\n".join(line.rstrip(" ") for line in result.split("\n")).strip()
        if self.casefold:
            result = result.casefold()
        if self.json_canonical:
            result = _canonical_json(result)
        return result
