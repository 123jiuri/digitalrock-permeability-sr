# Protocol and provenance

This code-only revision extracts the main sandstone LOPO search from the
author's archived `redesign_pipeline.py`, `parallel_full_run.py` and
`parallel_task_worker.py`. Its protocol reference is the configuration and
metadata for `f25_fixed_fold_shared`, rather than the earlier public package's
train/internal/external interface. The original research scripts and results
remain unchanged outside this repository.

## Protocol retained

- 20 descriptors, in their original input order; target `log10(k / m²)`.
- Ten complete-rock hold-outs, sorted by rock name.
- Search seeds: 41, 42, 43, 123, 456, 789, 1111, 2222, 3333, 4444, 5555, 6666.
- Sampling seeds: 700000 plus sorted fold index. One saved training table is
  shared across all search seeds in that fold.
- The original NumPy `default_rng` sampling sequence and row order are retained.
  Smaller rocks are resampled with replacement; maximum-size rocks are shuffled
  without replacement. Euler preprocessing is fitted on this balanced table.
- Training-only squared-error search; four arithmetic operators; maximum
  complexity 15; 500 iterations; 30 populations of 50 expressions;
  tournament size 15; parsimony 0.001; 64-bit arithmetic.
- Variable, constant and operator node costs are all 1. Constant optimization,
  simplification, BFGS settings, cycle count and stopping defaults are explicit in
  `search_options`. Each PySR task is serial and deterministic.
- Every returned Pareto member is retained, sorted by complexity and training
  loss. Metrics on held-out data are calculated only after fitting.

## Packaging changes

Local project paths are replaced by CLI arguments. The default input is one
explicit development-only table, with an optional merger for the original split
files. Filename matching is one-to-one, and independent-test rocks are refused.
Legacy descriptor aliases are removed. This avoids silently equating old names
with the canonical descriptor definitions.

Independent tests, carbonate runs, physical closure candidates, controls,
baselines and figure/manuscript builders are not copied. The generic algebraic
summary in this package is not the full manuscript's subsequent physical
classification or competitive-family selection procedure.

Hashes guard inputs, fold training tables, code, environments and completed
Pareto files. An output directory with an unknown or changed identity is refused.
Subprocesses isolate Julia tasks; status files are closed before workers exit.
Failures and partial task sets are retained and are not aggregated as complete.

## Run archive

Keep the input CSV separately together with its SHA-256, exact extraction
definitions, effective JSON configuration, Python versions, Julia executable and
version, Julia `Project.toml` and `Manifest.toml`, the generated fold tables and
all per-task outputs. The repository pins the core dependency versions, not every
transitive Julia dependency or machine-level numerical library.

Code tests establish implementation checks, not recovery of published scientific
results. A full rerun can be assessed only with the corresponding separately
supplied input table and runtime. Do not treat task-best held-out R² as a final
post-selection independent-test metric.
