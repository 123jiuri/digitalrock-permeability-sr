"""Fixed-fold/shared-table LOPO orchestration and isolated PySR tasks."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Set before NumPy and, in subprocesses, before Julia are imported.
for _name in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "JULIA_NUM_THREADS",
):
    os.environ[_name] = "1"

import numpy as np
import pandas as pd

from .descriptors import DESCRIPTOR_VERSION, PARAM_NAMES
from .evaluation import canonical_expression, evaluate_formula, metrics, used_descriptors
from .preprocessing import (
    fit_preprocessor,
    load_input,
    lopo_folds,
    parent_balanced_sample,
    transform_frame,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    pending.replace(path)


def package_versions():
    versions = {}
    for name in ["numpy", "pandas", "sympy", "scikit-learn", "pysr", "juliacall", "juliapkg"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def code_digest():
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    paths = sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"), root / "pyproject.toml"])
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for name in [
        "iterations",
        "maxsize",
        "populations",
        "population_size",
        "tournament_selection_n",
        "folds",
    ]:
        if not isinstance(cfg[name], int) or isinstance(cfg[name], bool) or cfg[name] < 1:
            raise ValueError(f"{name} must be a positive integer")
    if cfg["population_size"] <= cfg["tournament_selection_n"]:
        raise ValueError("population_size must exceed tournament_selection_n")
    if cfg["maxsize"] < 7:
        raise ValueError("PySR 1.5.10 requires maxsize of at least 7")
    if not cfg["seeds"] or len(set(cfg["seeds"])) != len(cfg["seeds"]):
        raise ValueError("Search seeds must be nonempty and unique")
    if any(
        not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 for seed in cfg["seeds"]
    ):
        raise ValueError("Search seeds must be nonnegative integers")
    if cfg["balance_sampling_mode"] != "fixed_per_fold_shared":
        raise ValueError("Only fixed_per_fold_shared sampling is supported")
    if cfg["descriptor_version"] != DESCRIPTOR_VERSION or cfg["target_unit"] != "m2":
        raise ValueError("Input descriptor version or target unit differs from this release")
    if cfg.get("lithology") != "sandstone":
        raise ValueError("Only the main sandstone search is included")
    if len(set(cfg["expected_rocks"])) != len(cfg["expected_rocks"]):
        raise ValueError("Duplicate configured rock names")
    if cfg["folds"] > len(cfg["expected_rocks"]) or len(cfg["expected_rocks"]) < 2:
        raise ValueError("Invalid number of folds or discovery rocks")
    if not np.isfinite(cfg["parsimony"]) or cfg["parsimony"] < 0:
        raise ValueError("Invalid parsimony")
    if not isinstance(cfg["balance_seed_base"], int) or cfg["balance_seed_base"] < 0:
        raise ValueError("Invalid balance seed base")
    return cfg


def slug(rock):
    return re.sub(r"[^A-Za-z0-9]+", "", rock)[:10] or "fold"


def task_dir(out, rock, seed):
    return Path(out) / "p" / slug(rock) / f"s{seed}"


def prepare(input_path, config_path, out):
    """Validate input, then create or verify the ten shared training tables."""
    input_path, out = Path(input_path).resolve(), Path(out).resolve()
    cfg = load_config(config_path)
    data, quality = load_input(input_path, cfg["expected_rocks"])
    folds = list(lopo_folds(data))[: cfg["folds"]]
    if len({slug(rock) for rock, _, _ in folds}) != len(folds):
        raise ValueError("Fold slugs collide; use distinct rock identifiers")
    identity = {
        "input_sha256": sha256(input_path),
        "config": cfg,
        "code_sha256": code_digest(),
        "packages": package_versions(),
        "python_version": platform.python_version(),
    }
    out.mkdir(parents=True, exist_ok=True)
    metadata_path = out / "experiment_metadata.json"
    existing = None
    if metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        if existing.get("run_identity") != identity:
            raise ValueError(
                "Resume refused: input, configuration, code or environment changed; choose a new output directory"
            )
    elif any(out.iterdir()):
        raise ValueError("Output directory is not empty and has no matching run metadata")
    balances = []
    tasks = []
    directory = out / "fold_balance_tables"
    directory.mkdir(exist_ok=True)
    for index, (rock, train, test) in enumerate(folds):
        path = directory / (slug(rock) + ".csv")
        seed = cfg["balance_seed_base"] + index
        if existing:
            entry = next(b for b in existing["balance_tables"] if b["fold"] == rock)
            if not path.exists() or sha256(path) != entry["sha256"]:
                raise ValueError(f"Missing or modified shared training table: {rock}")
        else:
            sampled = parent_balanced_sample(train, seed)
            sampled.to_csv(path, index=False)
        sampled = pd.read_csv(path)
        if set(sampled["rock_name"]) != set(train["rock_name"]) or not set(
            sampled["Filename"]
        ).issubset(train["Filename"]):
            raise ValueError("Shared training table violates the LOPO split")
        counts = sampled.groupby("rock_name").size()
        if counts.nunique() != 1 or int(counts.iloc[0]) != int(
            train.groupby("rock_name").size().max()
        ):
            raise ValueError("Shared training table is not rock balanced")
        balances.append(
            {
                "fold": rock,
                "fold_index": index,
                "balance_seed": seed,
                "file": path.relative_to(out).as_posix(),
                "sha256": sha256(path),
                "training_rocks": sorted(train["rock_name"].unique().tolist()),
                "training_rows_raw": len(train),
                "training_rows_balanced": len(sampled),
                "test_rows": len(test),
                "rows_per_training_rock": int(counts.iloc[0]),
            }
        )
        tasks.extend(
            {
                "fold": rock,
                "seed": int(s),
                "fold_index": index,
                "balance_file": path.relative_to(out).as_posix(),
                "balance_sha256": sha256(path),
            }
            for s in cfg["seeds"]
        )
    metadata = {
        "run_identity": identity,
        "input_file": str(input_path),
        "quality_control": quality,
        "started_utc": existing["started_utc"] if existing else now(),
        "balance_tables": balances,
        "command": list(sys.argv),
        "threads_per_task": 1,
        "task_count": len(tasks),
        "tasks": tasks,
        "held_out_data_used_during_search": False,
        "evaluation_scope": "development-rock LOPO search archive; family comparison may use held-out metrics; not an independent structure test",
        "sealed_external_loaded": False,
        "platform": platform.platform(),
    }
    if existing and existing.get("finished_utc"):
        metadata["finished_utc"] = existing["finished_utc"]
    write_json(metadata_path, metadata)
    return metadata


def configure_julia():
    project = Path(sys.prefix) / "julia_env"
    if (project / "Project.toml").exists():
        os.environ.setdefault("JULIA_PROJECT", str(project))
        os.environ.setdefault("PYTHON_JULIAPKG_PROJECT", str(project))
        exe = project / "pyjuliapkg/install/bin/julia.exe"
        if exe.exists():
            os.environ.setdefault("PYTHON_JULIACALL_EXE", str(exe))
            os.environ.setdefault("PYTHON_JULIAPKG_EXE", str(exe))
        os.environ.setdefault("PYTHON_JULIAPKG_OFFLINE", "yes")


def julia_environment():
    """Record available runtime details without resolving/installing packages."""
    exe = os.environ.get("PYTHON_JULIACALL_EXE") or os.environ.get("PYTHON_JULIAPKG_EXE")
    project = os.environ.get("PYTHON_JULIAPKG_PROJECT") or os.environ.get("JULIA_PROJECT")
    result = {
        "executable": exe,
        "project": project,
        "version": None,
        "project_sha256": None,
        "manifest_sha256": None,
    }
    if exe and Path(exe).is_file():
        try:
            result["version"] = subprocess.check_output(
                [exe, "--version"], text=True, timeout=15
            ).strip()
        except (OSError, subprocess.SubprocessError):
            result["version"] = "unavailable"
    if project:
        for filename, key in [
            ("Project.toml", "project_sha256"),
            ("Manifest.toml", "manifest_sha256"),
        ]:
            path = Path(project) / filename
            if path.is_file():
                result[key] = sha256(path)
    return result


def search_options(cfg, rock, seed, directory):
    return dict(
        niterations=cfg["iterations"],
        binary_operators=["+", "-", "*", "/"],
        unary_operators=[],
        maxsize=cfg["maxsize"],
        populations=cfg["populations"],
        population_size=cfg["population_size"],
        tournament_selection_n=cfg["tournament_selection_n"],
        parsimony=cfg["parsimony"],
        elementwise_loss="loss(prediction, target) = (prediction - target)^2",
        precision=64,
        complexity_of_operators={"+": 1, "-": 1, "*": 1, "/": 1},
        complexity_of_constants=1,
        complexity_of_variables=1,
        complexity_mapping=None,
        should_simplify=True,
        should_optimize_constants=True,
        optimizer_algorithm="BFGS",
        optimizer_nrestarts=2,
        optimizer_f_calls_limit=None,
        optimize_probability=0.14,
        optimizer_iterations=8,
        ncycles_per_iteration=380,
        warmup_maxsize_by=None,
        timeout_in_seconds=None,
        max_evals=None,
        early_stop_condition=None,
        random_state=int(seed),
        deterministic=True,
        parallelism="serial",
        progress=False,
        verbosity=0,
        model_selection="best",
        output_directory=str(directory),
        run_id=f"{slug(rock)}_{seed}",
    )


def run_task(out, rock, seed, model_cls=None):
    out = Path(out).resolve()
    directory = task_dir(out, rock, seed)
    directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        metadata = json.loads((out / "experiment_metadata.json").read_text(encoding="utf-8"))
        cfg = metadata["run_identity"]["config"]
        task = next(t for t in metadata["tasks"] if t["fold"] == rock and t["seed"] == seed)
        if sha256(metadata["input_file"]) != metadata["run_identity"]["input_sha256"]:
            raise ValueError("Input changed after planning")
        balance = out / task["balance_file"]
        if sha256(balance) != task["balance_sha256"]:
            raise ValueError("Shared training table changed after planning")
        data, _ = load_input(metadata["input_file"], cfg["expected_rocks"])
        test = data.loc[data["rock_name"].eq(rock)].reset_index(drop=True)
        train = pd.read_csv(balance)
        if rock in set(train["rock_name"]) or not set(train["Filename"]).issubset(
            data.loc[data["rock_name"].ne(rock), "Filename"]
        ):
            raise ValueError("Held-out rows entered the training table")
        pre = fit_preprocessor(train)
        x_train, y_train = transform_frame(train, pre)
        x_test, y_test = transform_frame(test, pre)
        options = search_options(cfg, rock, seed, directory)
        if model_cls is None:
            if importlib.metadata.version("pysr") != "1.5.10":
                raise RuntimeError("This search protocol requires PySR 1.5.10")
            configure_julia()
            from pysr import PySRRegressor

            model_cls = PySRRegressor
        model = model_cls(**options)
        model.fit(x_train.to_numpy(float), y_train, variable_names=PARAM_NAMES)
        rows = []
        for rank, (_, eq) in enumerate(
            model.equations_.sort_values(["complexity", "loss"]).iterrows(), 1
        ):
            expression = str(eq["equation"])
            canonical, skeleton = canonical_expression(expression)
            row = {
                "fold": rock,
                "seed": seed,
                "pareto_rank": rank,
                "formula": expression,
                "canonical_formula": canonical,
                "algebraic_skeleton": skeleton,
                "complexity": int(eq["complexity"]),
                "loss": float(eq["loss"]),
                "used_descriptors": ",".join(used_descriptors(expression)),
                "n_descriptors": len(used_descriptors(expression)),
            }
            for label, x, y in [("train", x_train, y_train), ("test", x_test, y_test)]:
                try:
                    prediction = evaluate_formula(expression, x)
                except Exception:
                    prediction = np.full(len(y), np.nan)
                row.update({label + "_" + k: v for k, v in metrics(y, prediction).items()})
            rows.append(row)
        if not rows:
            raise RuntimeError("PySR returned no Pareto records")
        table = directory / "pareto.csv"
        pd.DataFrame(rows).to_csv(table, index=False)
        write_json(
            directory / "run_metadata.json",
            {
                "fold": rock,
                "seed": seed,
                "balance_sha256": task["balance_sha256"],
                "preprocessing": pre.to_dict(),
                "search_options": options,
                "candidate_descriptors": PARAM_NAMES,
                "julia": julia_environment() if model_cls.__name__ == "PySRRegressor" else None,
                "rows_train_balanced": len(train),
                "rows_test": len(test),
                "finished_utc": now(),
            },
        )
        result = {
            "fold": rock,
            "seed": seed,
            "status": "completed",
            "pareto_rows": len(rows),
            "pareto_sha256": sha256(table),
            "balance_sha256": task["balance_sha256"],
            "run_identity": metadata["run_identity"],
            "elapsed_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        (directory / "failure.log").write_text(traceback.format_exc(), encoding="utf-8")
        result = {
            "fold": rock,
            "seed": seed,
            "status": "failed",
            "error": repr(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }
    write_json(directory / "task_status.json", result)
    return result


def task_complete(out, task, identity):
    directory = task_dir(out, task["fold"], task["seed"])
    try:
        status = json.loads((directory / "task_status.json").read_text(encoding="utf-8"))
        return (
            status["status"] == "completed"
            and status["run_identity"] == identity
            and status["balance_sha256"] == task["balance_sha256"]
            and status["pareto_sha256"] == sha256(directory / "pareto.csv")
            and (directory / "run_metadata.json").exists()
        )
    except (OSError, ValueError, KeyError):
        return False


def aggregate(out, metadata):
    from .families import write_summaries

    out = Path(out)
    if not all(task_complete(out, t, metadata["run_identity"]) for t in metadata["tasks"]):
        raise RuntimeError("Cannot aggregate an incomplete or modified task set")
    tables = [
        pd.read_csv(task_dir(out, t["fold"], t["seed"]) / "pareto.csv") for t in metadata["tasks"]
    ]
    formulas = pd.concat(tables, ignore_index=True)
    formulas.to_csv(out / "pareto_all.csv", index=False)
    write_summaries(formulas, out, expected_tasks=len(metadata["tasks"]))
    statuses = [
        json.loads(
            (task_dir(out, t["fold"], t["seed"]) / "task_status.json").read_text(encoding="utf-8")
        )
        for t in metadata["tasks"]
    ]
    pd.DataFrame([{k: v for k, v in s.items() if k != "run_identity"} for s in statuses]).to_csv(
        out / "task_manifest.csv", index=False
    )
    metadata["finished_utc"] = now()
    write_json(out / "experiment_metadata.json", metadata)


def execute(out, metadata, workers=1, max_tasks=None):
    """Subprocess isolation avoids Julia cleanup threads blocking later tasks."""
    if workers < 1:
        raise ValueError("workers must be positive")
    if max_tasks is not None and max_tasks < 1:
        raise ValueError("max_tasks must be positive")
    out = Path(out).resolve()
    metadata["workers"] = workers
    write_json(out / "experiment_metadata.json", metadata)
    pending = [t for t in metadata["tasks"] if not task_complete(out, t, metadata["run_identity"])]
    if max_tasks is not None:
        pending = pending[:max_tasks]
    worker = Path(__file__).resolve().parents[2] / "scripts" / "_lopo_worker.py"
    active = []
    try:
        while pending or active:
            while pending and len(active) < workers:
                task = pending.pop(0)
                directory = task_dir(out, task["fold"], task["seed"])
                directory.mkdir(parents=True, exist_ok=True)
                handle = (directory / "worker.log").open("w", encoding="utf-8")
                cmd = [
                    sys.executable,
                    str(worker),
                    "--output-dir",
                    str(out),
                    "--fold",
                    task["fold"],
                    "--seed",
                    str(task["seed"]),
                ]
                try:
                    process = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT)
                except Exception:
                    handle.close()
                    raise
                active.append((process, handle, task))
            remaining = []
            for process, handle, task in active:
                if process.poll() is None:
                    remaining.append((process, handle, task))
                    continue
                handle.close()
                good = task_complete(out, task, metadata["run_identity"])
                print(
                    json.dumps(
                        {
                            "fold": task["fold"],
                            "seed": task["seed"],
                            "status": "completed" if good else "failed",
                            "exit_code": process.returncode,
                        }
                    ),
                    flush=True,
                )
            active = remaining
            if active:
                time.sleep(0.2)
    finally:
        for process, handle, _ in active:
            if process.poll() is None:
                process.terminate()
                process.wait()
            handle.close()
    complete = sum(task_complete(out, t, metadata["run_identity"]) for t in metadata["tasks"])
    print(json.dumps({"completed": complete, "expected": len(metadata["tasks"])}), flush=True)
    if complete == len(metadata["tasks"]):
        aggregate(out, metadata)
        return 0
    return 2
