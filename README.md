# Digital-rock permeability: LOPO symbolic regression

Code for the main sandstone leave-one-rock-out (LOPO) symbolic-regression search.
The release contains source code, search configuration, documentation and synthetic
unit tests. It contains **no images, descriptor values, permeability labels, fitted
equations, prediction tables, figures or manuscript files**. Input data must be
supplied separately.

[中文说明](README.zh-CN.md) · [Input schema](docs/input_schema.md) · [Protocol and provenance](docs/reproducibility.md)

## Scope

The formal configuration uses 10 development sandstone rocks, 20 candidate
descriptors and 12 search seeds, giving 120 rock-by-seed tasks. For each fold:

1. Hold out every valid subvolume of one complete rock.
2. Generate one balanced training table from the other nine rocks. Use the sorted
   fold index plus 700000 as its sampling seed. All 12 searches share this table.
3. Fit preprocessing on that training table. Use base-10 logarithms for positive
   descriptors and permeability; transform signed Euler density with a
   training-derived inverse-hyperbolic-sine scale.
4. Search with PySR using `+`, `-`, `*`, `/`, no unary operators, and training loss
   only. Keep the entire returned Pareto front.
5. After the search, calculate metrics for every retained member on the complete
   held-out rock. Summarize records, task coverage and descriptor occurrence.

No descriptor combination or target equation is inserted into the search.
Family summaries are post-search algebraic summaries, not a physical grouping
used by the search. The code does not select a final equation for independent
testing. Development-rock LOPO scores may inform subsequent family comparisons;
they are not an independent test of the selected structure.

Carbonate searches, independent-test prediction, permutations, ablations,
controlled-dimension regression, machine-learning baselines, descriptor
extraction and plotting are outside this release.

## Environment

The reference environment is Python **3.13.13**, NumPy 2.1.3, pandas 3.0.2,
SymPy 1.14.0, scikit-learn 1.8.0, PySR 1.5.10, JuliaCall 0.9.26 and Juliapkg
0.1.23. The Julia reference versions are Julia 1.12.6, SymbolicRegression.jl
1.11.3, PythonCall.jl 0.9.26 and LoopVectorization.jl 0.12.173.

In a **new environment** using the reference Python version:

```bash
python -m pip install -e ".[sr]"
```

In the author's already provisioned environment, use its existing interpreter;
do not upgrade packages. The scripts can be run without installing this package.
PoreSpy, OpenPNM, XGBoost and LightGBM are not needed for this code-only LOPO stage.

PySR requires Julia and its packages. `julia/Project.toml` specifies the reference
core Julia dependencies, not a complete transitive lock. For a separate Julia
installation, instantiate that project once and point `JULIA_PROJECT`,
`PYTHON_JULIAPKG_PROJECT` and `PYTHON_JULIACALL_EXE` to the configured project and
executable as appropriate. Preserve the resulting local `Manifest.toml` with the
run archive; it is not included in Git. If the Python environment already has
`julia_env/Project.toml`, the runner reuses that environment offline rather than
silently resolving a different Julia project.

## Prepare an input table

Supply one CSV containing **only development sandstone subvolumes**, with
`Filename`, `rock_name`, `lithology`, `permeability`, and all 20 descriptor columns.
Units and validity checks are documented in [the input schema](docs/input_schema.md).
Do not concatenate the independent hold-out rocks into this table.

For the original two-root archive layout, a helper merges only `train` and
`internal_test`, checking a one-to-one ID match. It does not open `external_test`:

```bash
python scripts/prepare_discovery_input.py --numeric-root /path/to/numeric_tables --metadata-root /path/to/metadata_tables --output /path/to/local/discovery.csv
```

Both roots must contain `sandstone/train/complete_features.csv` and
`sandstone/internal_test/complete_features.csv`. Already merged inputs can be
used directly; the helper is optional. No raw-image processing or unit conversion
is performed here.

## Validate without starting a search

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --dry-run
```

This checks IDs, quality-control conditions, rock membership and fold isolation,
then writes one shared training table per fold and a run manifest. It does not
import PySR or start Julia. These generated files contain data and remain local.

## Run or resume the main search

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --workers 8
```

The default configuration is `configs/sandstone_lopo.json`: 500 iterations,
maximum complexity 15, 30 populations of 50 expressions, tournament size 15 and
parsimony 0.001. Each PySR task is deterministic and serial; `--workers` controls
independent task subprocesses, not threads within a task. On Windows, keep the
output path short enough for Julia/PySR checkpoint filenames.

Repeat the same command to resume. Completed tasks are verified by hashes and
skipped. A changed input, configuration, source code, Python version or recorded
package version requires a new output directory. Modified training tables are
rejected. Failed or interrupted tasks are not counted as completed.

`--max-tasks 1` runs at most one pending task; exit code 2 means the overall task
set is incomplete. Use `--aggregate-only` only after every configured task has
finished. Aggregation never labels a partial task set as a completed experiment.

## Local outputs

- `experiment_metadata.json`: input hash, effective configuration, code hash,
  environment versions, fold plans and task identities.
- `fold_balance_tables/`: the exact fold training tables shared across seeds.
- `p/<rock-slug>/s<seed>/`: raw PySR artifacts, complete `pareto.csv`, preprocessing
  metadata, task status and failure/worker logs.
- `pareto_all.csv`, `task_manifest.csv`, `task_summary.csv`: complete-run outputs.
- `descriptor_frequency.csv`: occurrence per Pareto record, counted once per
  descriptor per record, and separate rock-by-seed task coverage.
- `family_summary.csv`: task coverage of algebraic families. Affine forms in the
  transformed coordinates are grouped by slopes, ignoring intercepts; other
  forms use their normalized algebraic skeleton. No physical identity is implied.

All generated outputs are ignored by Git. Search equations refer to **transformed
coordinates**: the model predicts `log10(k / m²)`. An affine expression in log
inputs can be inverted to a power law; a nonlinear expression must retain its
actual inverse transform. Do not relabel it as an exact raw-variable formula.

Summaries can be rebuilt from a complete local archive:

```bash
python scripts/analyze_formula_families.py --input-dir results/sandstone_lopo --output-dir results/sandstone_summaries
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests generate synthetic rows in memory or temporary directories. They check
rock isolation, shared sampling, preprocessing, all-Pareto retention, resume
guards and aggregation. They do not require the study data or start Julia.
Successful tests do not establish that a new full search reproduces the archived
equation counts or predictive scores.

## PySR citation

Cranmer, M. (2023). *Interpretable machine learning for science with PySR and
SymbolicRegression.jl*. https://doi.org/10.48550/arXiv.2305.01582

The earlier generic train/internal/external interface remains recoverable in Git
history at commit `40690cb`; it is not the current LOPO entry point. The existing
MIT license is retained.
