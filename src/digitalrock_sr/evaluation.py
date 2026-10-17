"""Held-out metrics and equation parsing, separate from the search objective."""

import re

import numpy as np
import sympy as sp
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .descriptors import PARAM_NAMES


def metrics(y_true, y_pred):
    y_true = np.asarray(y_true, float).reshape(-1)
    prediction = np.asarray(y_pred, float).reshape(-1)
    empty = {name: np.nan for name in ["r2", "rmse", "mae", "bias", "calibration_slope"]}
    if prediction.shape != y_true.shape or not np.isfinite(prediction).all():
        return empty
    slope = (
        float(np.polyfit(y_true, prediction, 1)[0])
        if len(y_true) >= 2 and np.ptp(y_true) > 0
        else np.nan
    )
    return {
        "r2": float(r2_score(y_true, prediction)) if len(y_true) >= 2 else np.nan,
        "rmse": float(np.sqrt(mean_squared_error(y_true, prediction))),
        "mae": float(mean_absolute_error(y_true, prediction)),
        "bias": float(np.mean(prediction - y_true)),
        "calibration_slope": slope,
    }


def used_descriptors(expression):
    return [
        name
        for name in PARAM_NAMES
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", str(expression))
    ]


def parse_expression(expression):
    symbols = {name: sp.Symbol(name) for name in PARAM_NAMES}
    parsed = sp.sympify(str(expression).replace("^", "**"), locals=symbols)
    if parsed.free_symbols - set(symbols.values()):
        raise ValueError("Unknown symbol in equation")
    return parsed, symbols


def canonical_expression(expression):
    try:
        parsed, _ = parse_expression(expression)
        replacements = {v: sp.Float(f"{float(v):.6g}") for v in parsed.atoms(sp.Float)}
        parsed = sp.cancel(sp.together(parsed.xreplace(replacements)))
        canonical = sp.sstr(parsed, order="lex")
        skeleton = sp.sstr(
            parsed.xreplace({v: sp.Symbol("CONST") for v in parsed.atoms(sp.Number)}), order="lex"
        )
        return canonical, skeleton
    except (ValueError, TypeError, SyntaxError, sp.SympifyError):
        return str(expression), str(expression)


def evaluate_formula(expression, features):
    # Parse only trusted local PySR output. SymPy parsing is not a sandbox.
    parsed, symbols = parse_expression(expression)
    fn = sp.lambdify([symbols[n] for n in PARAM_NAMES], parsed, modules="numpy")
    with np.errstate(all="ignore"):
        pred = np.asarray(fn(*[features[n].to_numpy(float) for n in PARAM_NAMES]), float)
    if pred.ndim == 0:
        pred = np.full(len(features), float(pred))
    return pred.reshape(-1)
