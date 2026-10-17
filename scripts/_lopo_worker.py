"""Internal task process. Flush outputs before exiting around Julia cleanup."""

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from digitalrock_sr.lopo import run_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fold", required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    result = run_task(args.output_dir, args.fold, args.seed)
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    code = main()
    # Status, Pareto table and metadata have been closed; Julia may retain threads.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
