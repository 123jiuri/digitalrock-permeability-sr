"""Input validation and transformations used before symbolic regression."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .descriptors import PARAM_NAMES, POSITIVE_FEATURES


LEGACY_ALIASES = {
    "porosity_extracted": "porosity",
    "mean_local_thickness": "mean_pore_radius_voxel",
    "max_local_thickness": "max_thickness",
    "local_thickness_95th": "thickness_95th",
    "mean_pore_equivalent_radius": "mean_pore_radius_network",
    "mean_throat_equivalent_radius": "mean_throat_radius",
    "critical_percolating_throat_radius": "critical_throat_radius",
    "electrical_path_tortuosity": "electrical_tortuosity",
    "geometric_tortuosity": "tortuosity_geom",
    "largest_connected_pore_fraction": "connectivity_index",
    "euler_density": "euler_number",
    "mean_coordination_number": "mean_coordination",
    "median_throat_length_to_diameter": "throat_aspect_ratio_median",
    "s2_short_integral": "correlation_short",
    "s2_mid_integral": "correlation_mid",
    "s2_long_integral": "correlation_long",
    "pore_phase_fractal_dimension": "fractal_dimension",
}


def canonicalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for canonical, legacy in LEGACY_ALIASES.items():
        if canonical not in frame.columns and legacy in frame.columns:
            frame[canonical] = frame[legacy]
    return frame


@dataclass
class Preprocessor:
    positive_features: list[str]
    euler_asinh_scale: float
    target_transform: str = "log10(permeability)"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_columns(frame: pd.DataFrame, target_column: str = "permeability") -> None:
    frame = canonicalize_columns(frame)
    required = [target_column, *PARAM_NAMES]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def complete_cases(frame: pd.DataFrame, target_column: str = "permeability") -> pd.DataFrame:
    frame = canonicalize_columns(frame)
    validate_columns(frame, target_column)
    numeric = frame[[target_column, *PARAM_NAMES]].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    valid &= numeric[target_column].to_numpy(dtype=float) > 0
    for name in POSITIVE_FEATURES:
        valid &= numeric[name].to_numpy(dtype=float) > 0
    return frame.loc[valid].reset_index(drop=True)


def fit_preprocessor(frame: pd.DataFrame, target_column: str = "permeability") -> Preprocessor:
    frame = canonicalize_columns(frame)
    clean = complete_cases(frame, target_column)
    if clean.empty:
        raise ValueError("No complete positive rows are available for preprocessing")
    euler = clean["euler_density"].to_numpy(dtype=float)
    nonzero = np.abs(euler[euler != 0])
    scale = float(np.median(nonzero)) if len(nonzero) else 1.0
    return Preprocessor(list(POSITIVE_FEATURES), scale)


def transform_frame(
    frame: pd.DataFrame,
    preprocessor: Preprocessor,
    target_column: str = "permeability",
) -> tuple[pd.DataFrame, np.ndarray]:
    frame = canonicalize_columns(frame)
    clean = complete_cases(frame, target_column)
    if clean.empty:
        raise ValueError("No complete positive rows are available")
    transformed = pd.DataFrame(index=clean.index)
    for name in PARAM_NAMES:
        values = clean[name].to_numpy(dtype=float)
        if name == "euler_density":
            transformed[name] = np.arcsinh(values / preprocessor.euler_asinh_scale)
        else:
            transformed[name] = np.log10(values)
    target = np.log10(clean[target_column].to_numpy(dtype=float))
    return transformed[PARAM_NAMES], target
