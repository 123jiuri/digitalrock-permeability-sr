"""Metrics and formula helpers used by the public scripts."""

from __future__ import annotations

import re

import numpy as np
import sympy as sp
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .descriptors import DESCRIPTOR_CLASSES, PARAM_NAMES


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    prediction = np.asarray(y_pred, dtype=float).reshape(-1)
    if prediction.shape != y_true.shape or not np.isfinite(prediction).all():
        return {"R2": np.nan, "RMSE": np.nan, "MAE": np.nan}
    return {
        "R2": float(r2_score(y_true, prediction)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, prediction))),
        "MAE": float(mean_absolute_error(y_true, prediction)),
    }


def used_descriptors(expression: str) -> list[str]:
    return [
        name for name in PARAM_NAMES
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", expression)
    ]


def formula_skeleton(expression: str) -> str:
    number = r"(?<![A-Za-z0-9_])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
    return re.sub(number, "C", re.sub(r"\s+", "", expression))


def canonical_formula(expression: str, significant_digits: int = 8) -> str:
    symbols = {name: sp.Symbol(name) for name in PARAM_NAMES}
    parsed = sp.sympify(expression, locals=symbols)
    replacements = {
        value: sp.Float(f"{float(value):.{significant_digits}g}")
        for value in parsed.atoms(sp.Float)
    }
    return sp.sstr(sp.cancel(sp.together(parsed.xreplace(replacements))), order="lex")


def descriptor_class_counts(names: list[str]) -> dict[str, int]:
    return {
        f"n_{class_name}": sum(name in members_set for name in names)
        for class_name, members_set in DESCRIPTOR_CLASSES.items()
    }
