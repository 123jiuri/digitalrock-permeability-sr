#!/usr/bin/env python
"""Run repeated, data-independent-configuration PySR searches.

The script consumes user-provided CSV files but never ships or assumes the
study's private data directory. All search and preprocessing metadata are
written to the requested output directory.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

import numpy as np
import pandas as pd

from digitalrock_sr.descriptors import DESCRIPTOR_CLASSES, PARAM_NAMES
from digitalrock_sr.evaluation import (
    canonical_formula,
    descriptor_class_counts,
    formula_skeleton,
    metrics,
    used_descriptors,
)
from digitalrock_sr.preprocessing import fit_preprocessor, transform_frame


DEFAULT_SEEDS = [41, 42, 43, 123, 456, 789, 1111, 2222, 3333, 4444, 5555, 6666]


def package_versions() -> dict[str, str]:
    result = {}
    for name in ("pysr", "juliacall", "juliapkg", "sympy", "numpy", "pandas", "scikit-learn"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "not_installed"
    return result


def system_info() -> dict[str, object]:
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu_count": os.cpu_count(),
    }


def log(message: str, path: Path) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def evaluate_equation(row: pd.Series, transformed: dict[str, tuple[pd.DataFrame, np.ndarray]]) -> dict[str, float]:
    predictor = row.get("lambda_format")
    result: dict[str, float] = {}
    for split_name, (features, target) in transformed.items():
        try:
            values = predictor(features.to_numpy(dtype=float))
            split_metrics = metrics(target, values)
        except Exception:
            split_metrics = {"R2": np.nan, "RMSE": np.nan, "MAE": np.nan}
        for metric_name, value in split_metrics.items():
            result[f"{metric_name}_{split_name}"] = value
    return result


def run_seed(model_cls, seed: int, output_dir: Path, transformed: dict[str, tuple[pd.DataFrame, np.ndarray]], args: argparse.Namespace):
    train_x, train_y = transformed["train"]
    model = model_cls(
        niterations=args.iterations,
        binary_operators=["+", "-", "*", "/"],
        unary_operators=[],
        maxsize=args.maxsize,
        populations=args.populations,
        population_size=args.population_size,
        tournament_selection_n=args.tournament_selection_n,
        parsimony=args.parsimony,
        elementwise_loss="loss(prediction, target) = (prediction - target)^2",
        precision=64,
        random_state=seed,
        deterministic=True,
        parallelism="serial",
        progress=False,
        verbosity=0,
        model_selection="best",
        warm_start=False,
        output_directory=str(output_dir / "pysr_runs"),
        run_id=f"seed_{seed}",
    )
    started = time.perf_counter()
    model.fit(train_x.to_numpy(dtype=float), train_y, variable_names=list(train_x.columns))
    elapsed = time.perf_counter() - started
    equations = model.equations_.copy().sort_values(["complexity", "loss"])
    records = []
    for rank, (_, row) in enumerate(equations.iterrows(), start=1):
        expression = str(row["equation"])
        names = used_descriptors(expression)
        records.append({
            "seed": seed,
            "pareto_rank": rank,
            "formula": expression,
            "formula_key": "".join(expression.split()),
            "formula_canonical_8sig": canonical_formula(expression),
            "formula_skeleton": formula_skeleton(expression),
            "complexity": int(row["complexity"]),
            "loss": float(row["loss"]),
            "score": float(row["score"]) if np.isfinite(row.get("score", np.nan)) else np.nan,
            "n_descriptors": len(names),
            "used_descriptors": ",".join(names),
            "fit_elapsed_seconds": elapsed,
            **descriptor_class_counts(names),
            **evaluate_equation(row, transformed),
        })
    frame = pd.DataFrame(records)
    best = frame.loc[frame["R2_train"].idxmax()]
    summary = {
        "seed": seed,
        "fit_elapsed_seconds": elapsed,
        "pareto_formula_count": len(frame),
        "best_formula": best["formula"],
        "best_complexity": int(best["complexity"]),
        "best_R2_train": float(best["R2_train"]),
        "best_R2_internal": float(best.get("R2_internal", np.nan)),
        "best_R2_external": float(best.get("R2_external", np.nan)),
    }
    return frame, summary


def write_summaries(output_dir: Path, formulas: pd.DataFrame, seeds: pd.DataFrame, threshold: float) -> None:
    formulas.to_csv(output_dir / "formulas_all.csv", index=False)
    seeds.to_csv(output_dir / "seed_summary.csv", index=False)
    train = formulas["R2_train"]
    unique = formulas.drop_duplicates("formula_key")
    high = unique[unique["R2_train"] >= threshold]
    rows = []
    for name in PARAM_NAMES:
        pattern = rf"(?:^|,){name}(?:,|$)"
        mask = unique["used_descriptors"].fillna("").str.contains(pattern, regex=True)
        high_mask = high["used_descriptors"].fillna("").str.contains(pattern, regex=True)
        seed_mask = formulas["used_descriptors"].fillna("").str.contains(pattern, regex=True)
        seed_coverage = formulas.loc[seed_mask, "seed"].nunique()
        rows.append({
            "descriptor": name,
            "descriptor_class": next(cls for cls, members in DESCRIPTOR_CLASSES.items() if name in members),
            "unique_formula_fraction": float(mask.mean()) if len(unique) else 0.0,
            "high_R2_formula_fraction": float(high_mask.mean()) if len(high) else 0.0,
            "seed_coverage_count": int(seed_coverage),
            "seed_coverage_fraction": float(seed_coverage / seeds["seed"].nunique()),
        })
    pd.DataFrame(rows).sort_values("high_R2_formula_fraction", ascending=False).to_csv(output_dir / "descriptor_frequency.csv", index=False)
    family = formulas.groupby("formula_canonical_8sig").agg(
        occurrence_count=("formula", "size"),
        seed_coverage=("seed", "nunique"),
        min_complexity=("complexity", "min"),
        best_R2_train=("R2_train", "max"),
        median_R2_internal=("R2_internal", "median"),
        median_R2_external=("R2_external", "median"),
        example_formula=("formula", "first"),
    ).reset_index().sort_values(["seed_coverage", "best_R2_train"], ascending=False)
    family.to_csv(output_dir / "formula_family_frequency.csv", index=False)
    family[family["seed_coverage"] == seeds["seed"].nunique()].to_csv(output_dir / "stable_formula_families.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--internal-csv", type=Path)
    parser.add_argument("--external-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--maxsize", type=int, default=15)
    parser.add_argument("--populations", type=int, default=30)
    parser.add_argument("--population-size", type=int, default=50)
    parser.add_argument("--tournament-selection-n", type=int, default=15)
    parser.add_argument("--parsimony", type=float, default=0.001)
    parser.add_argument("--high-r2-threshold", type=float, default=0.95)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.population_size <= args.tournament_selection_n:
        parser.error("--population-size must exceed --tournament-selection-n")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "experiment.log"
    log_path.write_text("", encoding="utf-8")
    frames = {"train": pd.read_csv(args.train_csv)}
    if args.internal_csv:
        frames["internal"] = pd.read_csv(args.internal_csv)
    if args.external_csv:
        frames["external"] = pd.read_csv(args.external_csv)
    preprocessor = fit_preprocessor(frames["train"])
    transformed = {name: transform_frame(frame, preprocessor) for name, frame in frames.items()}
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": " ".join(sys.argv),
        "input_files": {name: str(path.resolve()) for name, path in (("train", args.train_csv), ("internal", args.internal_csv), ("external", args.external_csv)) if path},
        "preprocessing": preprocessor.to_dict(),
        "system": system_info(),
        "python_packages": package_versions(),
        "search": vars(args) | {"seeds": args.seeds},
    }
    metadata["search"]["output_dir"] = str(args.output_dir.resolve())
    metadata["search"] = {key: (str(value) if isinstance(value, Path) else value) for key, value in metadata["search"].items()}
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    log(f"Prepared {len(transformed['train'][0])} training rows and {len(PARAM_NAMES)} descriptors", log_path)
    if args.dry_run:
        log("Dry run completed before importing PySR", log_path)
        return 0
    try:
        from pysr import PySRRegressor
        all_frames, summaries = [], []
        for seed in args.seeds:
            log(f"Starting seed={seed}", log_path)
            frame, summary = run_seed(PySRRegressor, seed, args.output_dir, transformed, args)
            all_frames.append(frame)
            summaries.append(summary)
            log(f"Finished seed={seed}; Pareto={len(frame)}; best train R2={summary['best_R2_train']:.6f}", log_path)
        formulas = pd.concat(all_frames, ignore_index=True)
        for column in ("R2_internal", "RMSE_internal", "MAE_internal", "R2_external", "RMSE_external", "MAE_external"):
            if column not in formulas.columns:
                formulas[column] = np.nan
        seed_frame = pd.DataFrame(summaries)
        write_summaries(args.output_dir, formulas, seed_frame, args.high_r2_threshold)
        metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        return 0
    except Exception:
        log(traceback.format_exc(), log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
