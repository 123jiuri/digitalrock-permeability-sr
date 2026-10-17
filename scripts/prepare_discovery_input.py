"""Merge existing canonical train/internal tables; never open external-test files."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from digitalrock_sr.descriptors import DEVELOPMENT_ROCKS
from digitalrock_sr.preprocessing import complete_cases


def prepare_input(numeric_root, metadata_root, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite an input table")
    parts = []
    for subset in ("train", "internal_test"):
        numeric = pd.read_csv(Path(numeric_root) / "sandstone" / subset / "complete_features.csv")
        metadata = pd.read_csv(
            Path(metadata_root) / "sandstone" / subset / "complete_features.csv",
            usecols=["Filename", "rock_name", "lithology", "resolution_um"],
        )
        if numeric["Filename"].duplicated().any() or metadata["Filename"].duplicated().any():
            raise ValueError("Duplicate subvolume ID in source table")
        if set(numeric["Filename"]) != set(metadata["Filename"]):
            raise ValueError("Numeric/metadata ID mismatch")
        overlap = set(numeric) & (set(metadata) - {"Filename"})
        merged = numeric.merge(
            metadata, on="Filename", validate="one_to_one", suffixes=("", "_metadata")
        )
        for name in overlap:
            if not merged[name].equals(merged[name + "_metadata"]):
                raise ValueError(f"Conflicting metadata column: {name}")
            merged = merged.drop(columns=name + "_metadata")
        parts.append(merged)
    joined = pd.concat(parts, ignore_index=True)
    clean = complete_cases(joined)
    if set(clean["rock_name"]) != set(DEVELOPMENT_ROCKS):
        raise ValueError("Unexpected discovery rocks")
    output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output, index=False)
    print(
        f"Prepared {len(clean)} valid subvolumes from {clean['rock_name'].nunique()} rocks; excluded {len(joined)-len(clean)} invalid rows"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-root", type=Path, required=True)
    parser.add_argument("--metadata-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_input(args.numeric_root, args.metadata_root, args.output)


if __name__ == "__main__":
    main()
