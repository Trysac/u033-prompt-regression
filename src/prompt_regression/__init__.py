"""Compare recorded outputs of two prompt versions and report the cases that changed."""

from __future__ import annotations

import logging

from prompt_regression.comparison import CaseDiff, Status, compare
from prompt_regression.errors import RegressionError
from prompt_regression.loader import RunRecord, load_run
from prompt_regression.normalizer import Normalizer
from prompt_regression.report import render

__all__ = [
    "CaseDiff",
    "Normalizer",
    "RegressionError",
    "RunRecord",
    "Status",
    "__version__",
    "compare",
    "load_run",
    "render",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
