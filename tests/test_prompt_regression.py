"""Behavior tests for the public API of prompt_regression."""

from __future__ import annotations

import pytest

import prompt_regression


def test_normalize_trims_and_lowercases() -> None:
    assert prompt_regression.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        prompt_regression.normalize(value)


def test_version_is_semver() -> None:
    parts = prompt_regression.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
