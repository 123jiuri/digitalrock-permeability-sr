"""Canonical formula-family analysis for PySR output tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .descriptors import descriptor_class
from .evaluation import canonical_formula, formula_skeleton


def parse_descriptors(value: object) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def analyze_formula_families(input_dir: Path, output_dir: Path, lithology: str) -> pd.DataFrame:
    formulas = pd.read_csv(input_dir / "formulas_all.csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    if "formula_canonical_8sig" not in formulas.columns:
        formulas["formula_canonical_8sig"] = formulas["formula"].map(canonical_formula)
    if "formula_skeleton" not in formulas.columns:
        formulas["formula_skeleton"] = formulas["formula"].map(formula_skeleton)

    train_col = f"R2_{lithology}_train"
    internal_col = f"R2_{lithology}_internal"
    external_col = f"R2_{lithology}_external"
    records = []
    seed_count = formulas["seed"].nunique()
    for family, frame in formulas.groupby("formula_canonical_8sig", dropna=False):
        descriptors = sorted({d for value in frame["used_descriptors"] for d in parse_descriptors(value)})
        classes = sorted({descriptor_class(d) for d in descriptors})
        has_geometry = "characteristic_geometric" in classes
        has_transport = "connectivity_transport" in classes
        has_spatial = "spatial_organization_complexity" in classes
        if not descriptors:
            block = "constant"
        elif has_geometry and has_transport:
            block = "geometry + transport"
        elif has_geometry:
            block = "geometry only"
        elif has_transport:
            block = "transport only"
        else:
            block = "other"
        if has_spatial and descriptors:
            block += " + spatial"
        row = {
            "formula_family": family,
            "occurrence_count": len(frame),
            "seed_coverage": frame["seed"].nunique(),
            "seed_coverage_fraction": frame["seed"].nunique() / seed_count,
            "min_complexity": frame["complexity"].min(),
            "descriptor_count": len(descriptors),
            "descriptors": ",".join(descriptors),
            "descriptor_classes": ",".join(classes),
            "functional_block": block,
            "example_formula": frame.iloc[0]["formula"],
        }
        for column, reducer in ((train_col, "max"), (internal_col, "median"), (external_col, "median")):
            if column in frame.columns:
                row[column] = getattr(frame[column], reducer)()
        if train_col in frame.columns:
            row["high_R2_count"] = int((frame[train_col] >= 0.95).sum())
        records.append(row)

    summary = pd.DataFrame(records).sort_values(
        ["seed_coverage", "min_complexity"], ascending=[False, True]
    )
    summary.to_csv(output_dir / "family_summary.csv", index=False)
    if train_col in summary.columns:
        summary[summary[train_col] >= 0.95].to_csv(
            output_dir / "high_performance_family_summary.csv", index=False
        )
    summary.groupby("functional_block", dropna=False).agg(
        family_count=("formula_family", "count"),
        max_seed_coverage=("seed_coverage", "max"),
        high_R2_families=("high_R2_count", lambda values: int((values > 0).sum()) if len(values) else 0),
    ).reset_index().to_csv(output_dir / "functional_block_summary.csv", index=False)
    return summary
