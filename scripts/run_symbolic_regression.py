#!/usr/bin/env python
"""Run the main rock-grouped LOPO symbolic-regression search."""
import argparse
import json
import os
from pathlib import Path
import sys

for name in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "JULIA_NUM_THREADS",
):
    os.environ[name] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digitalrock_sr.lopo import aggregate, execute, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        type=Path,
        required=True,
        help="Only development sandstone rows; see docs/input_schema.md",
    )
    parser.add_argument("--config", type=Path, default=ROOT / "configs/sandstone_lopo.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--workers", type=int, default=1, help="Concurrent isolated tasks; each task is serial"
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        help="Limit newly executed tasks; resume with the same command without this flag",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate folds and shared balance tables without importing PySR",
    )
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.max_tasks is not None and args.max_tasks < 1):
        parser.error("workers and max-tasks must be positive")
    metadata = prepare(args.input_csv, args.config, args.output_dir)
    print(
        json.dumps(
            {
                "quality_control": metadata["quality_control"],
                "folds": len(metadata["balance_tables"]),
                "tasks": metadata["task_count"],
            }
        ),
        flush=True,
    )
    if args.dry_run:
        return 0
    if args.aggregate_only:
        aggregate(args.output_dir, metadata)
        return 0
    return execute(args.output_dir, metadata, args.workers, args.max_tasks)


if __name__ == "__main__":
    raise SystemExit(main())
