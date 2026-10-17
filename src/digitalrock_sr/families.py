"""Post-search algebraic summaries; no physical labels or formula is prescribed."""

import json
from pathlib import Path

import pandas as pd
import sympy as sp

from .descriptors import PARAM_NAMES
from .evaluation import canonical_expression, parse_expression, used_descriptors


def family_key(expression):
    """Ignore intercepts in affine search-coordinate forms; retain slopes.

    Other expressions use the normalized algebraic skeleton. This is a generic
    algebraic summary, not the manuscript's separate physical classification.
    """
    canonical, skeleton = canonical_expression(expression)
    try:
        expr, symbols = parse_expression(canonical)
        coefficients = []
        for name in PARAM_NAMES:
            coefficient = sp.diff(expr, symbols[name])
            if coefficient.free_symbols:
                return "skeleton:" + skeleton
            value = float(coefficient)
            if abs(value) > 1e-10:
                coefficients.append((name, f"{value:.6g}"))
        return "affine:" + json.dumps(coefficients, separators=(",", ":"))
    except (ValueError, TypeError, sp.SympifyError):
        return "skeleton:" + skeleton


def write_summaries(formulas, output_dir, expected_tasks=None):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    required = {"fold", "seed", "formula", "complexity", "test_r2", "train_r2"}
    if required - set(formulas):
        raise ValueError(f"Missing Pareto columns: {sorted(required-set(formulas))}")
    if formulas.empty:
        raise ValueError("No Pareto records")
    tasks = formulas[["fold", "seed"]].drop_duplicates()
    total = len(tasks)
    if expected_tasks is not None and total != expected_tasks:
        raise ValueError("Task coverage does not match the completed run manifest")
    frame = formulas.copy()
    frame["family_key"] = frame["formula"].map(family_key)
    frequencies = []
    descriptors = frame["formula"].map(used_descriptors)
    for name in PARAM_NAMES:
        mask = descriptors.map(lambda names: name in names)
        cover = frame.loc[mask, ["fold", "seed"]].drop_duplicates()
        frequencies.append(
            {
                "descriptor": name,
                "records_containing_descriptor": int(mask.sum()),
                "pareto_record_count": len(frame),
                "record_fraction": float(mask.mean()),
                "tasks_containing_descriptor": len(cover),
                "total_tasks": total,
                "task_fraction": len(cover) / total,
            }
        )
    pd.DataFrame(frequencies).sort_values("records_containing_descriptor", ascending=False).to_csv(
        out / "descriptor_frequency.csv", index=False
    )
    records = []
    for key, group in frame.groupby("family_key", sort=True):
        per_task = group.groupby(["fold", "seed"])["test_r2"].median()
        records.append(
            {
                "family_key": key,
                "pareto_records": len(group),
                "task_coverage": len(per_task),
                "total_tasks": total,
                "task_fraction": len(per_task) / total,
                "fold_coverage": group["fold"].nunique(),
                "seed_coverage": group["seed"].nunique(),
                "min_complexity": int(group["complexity"].min()),
                "median_task_held_out_r2": float(per_task.median()),
                "example_formula": group.iloc[0]["formula"],
            }
        )
    pd.DataFrame(records).sort_values(
        ["task_coverage", "min_complexity"], ascending=[False, True]
    ).to_csv(out / "family_summary.csv", index=False)
    frame.groupby(["fold", "seed"], as_index=False).agg(
        pareto_records=("formula", "size"),
        best_training_r2=("train_r2", "max"),
        best_held_out_r2=("test_r2", "max"),
    ).to_csv(out / "task_summary.csv", index=False)
    combos = frame.assign(descriptor_combination=descriptors.map(lambda names: ",".join(names)))
    combos.groupby("descriptor_combination", as_index=False).agg(
        pareto_records=("formula", "size")
    ).to_csv(out / "descriptor_combinations.csv", index=False)
    return pd.DataFrame(records)


def analyze_formula_families(input_dir, output_dir):
    source = Path(input_dir)
    metadata = json.loads((source / "experiment_metadata.json").read_text(encoding="utf-8"))
    from .lopo import task_complete

    if not all(task_complete(source, t, metadata["run_identity"]) for t in metadata["tasks"]):
        raise ValueError("Analyze only a complete, unmodified LOPO task archive")
    # Re-read authoritative per-task outputs instead of trusting an edited aggregate.
    from .lopo import task_dir

    frame = pd.concat(
        [
            pd.read_csv(task_dir(source, t["fold"], t["seed"]) / "pareto.csv")
            for t in metadata["tasks"]
        ],
        ignore_index=True,
    )
    return write_summaries(frame, output_dir, metadata["task_count"])
