#!/usr/bin/env python
"""CLI for canonical formula-family post-processing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from digitalrock_sr.families import analyze_formula_families


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lithology", default="dataset")
    args = parser.parse_args()
    summary = analyze_formula_families(args.input_dir, args.output_dir, args.lithology)
    print(summary.head(12).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
