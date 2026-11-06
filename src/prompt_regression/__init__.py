"""Compare recorded outputs of two prompt versions over the same dataset and report unchanged, changed, improved, regressed, added and removed cases"""

from __future__ import annotations

__all__ = ["__version__", "normalize"]

__version__ = "0.1.0"


def normalize(value: str) -> str:
    """Return ``value`` trimmed and lower-cased.

    Placeholder API created by the template: replace it with the utility's real behavior.

    Raises:
        ValueError: if ``value`` is empty or only whitespace.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("value must not be empty")
    return cleaned.lower()
