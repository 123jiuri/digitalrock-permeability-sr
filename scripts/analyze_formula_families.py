"""Summarize complete LOPO Pareto records without a performance filter."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from digitalrock_sr.families import analyze_formula_families


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = analyze_formula_families(args.input_dir, args.output_dir)
    print(f"Summarized {len(summary)} algebraic families")


if __name__ == "__main__":
    main()
