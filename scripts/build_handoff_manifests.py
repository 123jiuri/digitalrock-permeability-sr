"""Build machine-readable inventories for the local research handoff.

The script records relative paths, sizes and SHA-256 checksums for files that
can be hashed without excessive runtime. Large raw volumes are indexed without
reading their contents; their paths and sizes remain available for a later
data-repository upload.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "RESEARCH_HANDOFF_20260805"
MANIFESTS = HANDOFF / "manifests"
HASH_LIMIT = 5 * 1024 * 1024


def sha256(path: Path) -> str:
    if path.suffix.lower() in {".raw", ".png", ".svg", ".pdf", ".pkl", ".npz", ".npy", ".bak", ".log"}:
        return "not_computed_binary_or_image"
    if path.stat().st_size > HASH_LIMIT:
        return "not_computed_large_file"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    code_roots = [ROOT, ROOT / "experiments", ROOT / "figures"]
    code_rows: list[dict[str, object]] = []
    seen: set[Path] = set()
    for base in code_roots:
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts or path in seen:
                continue
            seen.add(path)
            role = "root_script" if base == ROOT else ("experiment_script" if "experiments" in path.parts else "figure_script")
            code_rows.append({
                "relative_path": rel(path),
                "role": role,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    write_rows(MANIFESTS / "CODE_INDEX.csv", sorted(code_rows, key=lambda row: str(row["relative_path"])),
               ["relative_path", "role", "bytes", "sha256"])

    data_roots = [ROOT / "data", ROOT / "final_results_20260803", ROOT / "experiments" / "results",
                  ROOT / "figures", ROOT / "tables"]
    data_rows: list[dict[str, object]] = []
    for base in data_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in {".csv", ".json", ".md", ".txt", ".npz", ".pkl", ".png", ".svg", ".pdf", ".npy", ".raw", ".log", ".bak"}:
                continue
            category = "raw_image" if path.suffix.lower() == ".raw" else "machine_readable_or_report"
            data_rows.append({
                "relative_path": rel(path),
                "category": category,
                "extension": path.suffix.lower(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    write_rows(MANIFESTS / "DATA_INDEX.csv", sorted(data_rows, key=lambda row: str(row["relative_path"])),
               ["relative_path", "category", "extension", "bytes", "sha256"])

    raw_rows = [row for row in data_rows if row["category"] == "raw_image"]
    write_rows(MANIFESTS / "RAW_IMAGE_INDEX.csv", raw_rows,
               ["relative_path", "category", "extension", "bytes", "sha256"])

    source_registry = ROOT / "github_package" / "docs" / "EXPERIMENT_REGISTRY.csv"
    target_registry = MANIFESTS / "EXPERIMENT_REGISTRY.csv"
    target_registry.write_bytes(source_registry.read_bytes())

    print(f"Wrote {len(code_rows)} code rows, {len(data_rows)} data rows and {len(raw_rows)} raw-image rows")


if __name__ == "__main__":
    main()
