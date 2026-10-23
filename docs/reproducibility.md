# Reproducibility

The LOPO workflow follows the archived `f25_fixed_fold_shared` search protocol,
implemented here as command-line scripts with a development-only input table.

## Search protocol

- Use the 20 descriptors in their recorded input order and target `log10(k / m²)`.
- Sort rocks by name and hold out one complete rock per fold.
- Set the sampling seed to 700000 plus the sorted fold index. Smaller training
  rocks are sampled with replacement to match the largest count; maximum-size
  rocks are shuffled without replacement.
- Save one balanced training table per fold and share it across seeds 41, 42,
  43, 123, 456, 789, 1111, 2222, 3333, 4444, 5555 and 6666.
- Fit preprocessing on that table and apply it unchanged to the held-out rock.
- Search using training squared error, four arithmetic operators, maximum
  complexity 15, 500 iterations, 30 populations of 50 expressions, tournament
  size 15, parsimony 0.001 and 64-bit arithmetic.
- Run each PySR task serially with deterministic execution. Variable, constant
  and operator costs are 1; additional optimizer settings are recorded in
  `search_options` in the run metadata.
- Retain every returned Pareto member and calculate held-out metrics after
  fitting. These metrics support development-stage family comparisons;
  independent evaluation of a selected equation is a separate stage.

Expressions predict log permeability from transformed descriptors. Affine
expressions in log inputs can be converted to power laws; nonlinear expressions
use their actual inverse transform. Family summaries group affine forms by
slopes and other forms by normalized algebraic skeleton.

## Reference environment

Python 3.13.13; NumPy 2.1.3; pandas 3.0.2; SymPy 1.14.0;
scikit-learn 1.8.0; PySR 1.5.10; JuliaCall 0.9.26; Juliapkg 0.1.23.
Julia 1.12.6; SymbolicRegression.jl 1.11.3; PythonCall.jl 0.9.26;
LoopVectorization.jl 0.12.173.

`julia/Project.toml` specifies the core Julia dependencies. For a separate Julia
installation, instantiate the project and configure `JULIA_PROJECT`,
`PYTHON_JULIAPKG_PROJECT` and `PYTHON_JULIACALL_EXE` for the project and executable.
The runner also supports an existing `julia_env/Project.toml` in the Python
environment, which it reuses offline. Save the resolved Julia `Manifest.toml`
with each local run archive to record transitive dependencies.

## Run archive and resuming

The runner records input, configuration, source-code and environment identities,
along with the shared training tables and per-task outputs. Repeat the same
command to resume: completed tasks are checked by hashes and skipped, while
pending tasks run in isolated subprocesses. A changed run identity requires a
new output directory.

`--dry-run` prepares folds and validates inputs without starting Julia.
`--max-tasks 1` runs at most one pending task; exit code 2 indicates an incomplete
task set. `--aggregate-only` rebuilds summaries once every task is complete.

Keep the input CSV, descriptor definitions, generated metadata, Python and Julia
versions, Julia project and manifest, fold tables and per-task outputs together
in the local run archive. The unit tests check implementation behavior with
synthetic inputs; assessing a full scientific rerun also requires the study
input table and runtime.
