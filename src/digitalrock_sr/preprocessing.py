"""Canonical input validation and training-only transformations."""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .descriptors import DEVELOPMENT_ROCKS, PARAM_NAMES, POSITIVE_FEATURES, SEALED_ROCKS


def complete_cases(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["Filename", "rock_name", "lithology", "permeability", *PARAM_NAMES]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if frame[["Filename", "rock_name", "lithology"]].isna().any().any():
        raise ValueError("Missing subvolume ID, rock name, or lithology")
    if frame["Filename"].astype(str).str.strip().eq("").any():
        raise ValueError("Empty subvolume ID")
    if frame["Filename"].duplicated().any():
        raise ValueError("Duplicate subvolume ID")
    if set(frame["rock_name"]) & SEALED_ROCKS:
        raise ValueError("Independent hold-out sandstone entered discovery input")
    if not frame["lithology"].eq("sandstone").all():
        raise ValueError("This release accepts sandstone discovery rows only")
    numeric = frame[["permeability", *PARAM_NAMES]].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy(float)).all(axis=1)
    valid &= numeric["permeability"].gt(0).to_numpy()
    valid &= numeric[POSITIVE_FEATURES].gt(0).all(axis=1).to_numpy()
    result = frame.loc[valid].copy()
    result[numeric.columns] = numeric.loc[valid]
    result = result.reset_index(drop=True)
    if result.empty:
        raise ValueError("No valid discovery rows")
    if set(result["rock_name"]) != set(frame["rock_name"]):
        raise ValueError("Quality control removed an entire rock")
    return result


def load_input(path, expected_rocks=DEVELOPMENT_ROCKS):
    raw = pd.read_csv(path)
    frame = complete_cases(raw)
    if set(frame["rock_name"]) != set(expected_rocks):
        raise ValueError("Input rock names do not match the configured discovery rocks")
    return frame, {
        "input_rows": len(raw),
        "valid_rows": len(frame),
        "excluded_rows": len(raw) - len(frame),
    }


def lopo_folds(frame):
    if frame["rock_name"].nunique() < 2:
        raise ValueError("LOPO requires at least two rocks")
    for rock in sorted(frame["rock_name"].unique()):
        train = frame.loc[frame["rock_name"].ne(rock)].reset_index(drop=True)
        test = frame.loc[frame["rock_name"].eq(rock)].reset_index(drop=True)
        assert set(train["rock_name"]).isdisjoint(test["rock_name"])
        yield rock, train, test


def parent_balanced_sample(frame, seed):
    """Archived RNG/order: oversample smaller rocks, permute largest rocks.

    Smaller rocks are sampled with replacement, which can repeat or omit rows.
    The resulting counts, rather than the number of unique IDs, are equal.
    """
    rng = np.random.default_rng(seed)
    target = int(frame.groupby("rock_name").size().max())
    chunks = []
    for rock in sorted(frame["rock_name"].unique()):
        group = frame.loc[frame["rock_name"].eq(rock)]
        indices = rng.choice(len(group), size=target, replace=len(group) < target)
        chunks.append(group.iloc[indices])
    return pd.concat(chunks, ignore_index=True)


@dataclass(frozen=True)
class Preprocessor:
    euler_scale: float
    positive_transform: str = "log10(x / reporting_unit)"
    signed_transform: str = "asinh(euler_density / training_median_abs_nonzero)"
    target_transform: str = "log10(k / m^2)"

    def to_dict(self):
        return asdict(self)


def fit_preprocessor(train):
    values = train["euler_density"].to_numpy(float)
    nonzero = np.abs(values[values != 0])
    if not len(nonzero) or not np.isfinite(nonzero).all():
        raise ValueError("Euler scale is undefined for this training table")
    return Preprocessor(float(np.median(nonzero)))


def transform_frame(frame, preprocessor):
    """Transform validated rows without silently removing or reordering any."""
    if not np.isfinite(preprocessor.euler_scale) or preprocessor.euler_scale <= 0:
        raise ValueError("Invalid fitted Euler scale")
    out = pd.DataFrame(index=frame.index)
    for name in PARAM_NAMES:
        values = frame[name].to_numpy(float)
        if not np.isfinite(values).all():
            raise ValueError(f"Nonfinite descriptor: {name}")
        if name == "euler_density":
            out[name] = np.arcsinh(values / preprocessor.euler_scale)
        else:
            if np.any(values <= 0):
                raise ValueError(f"Nonpositive descriptor: {name}")
            out[name] = np.log10(values)
    k = frame["permeability"].to_numpy(float)
    if not np.isfinite(k).all() or np.any(k <= 0):
        raise ValueError("Invalid permeability")
    return out[PARAM_NAMES], np.log10(k)
