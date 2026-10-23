# Digital-rock permeability: LOPO symbolic regression

PySR code for discovering permeability equations from sandstone pore-structure
descriptors, using leave-one-rock-out (LOPO) evaluation. The repository contains
the main search workflow, configuration and tests. Input data are supplied
separately; data and generated results stay local.

[中文说明](README.zh-CN.md) · [Input schema](docs/input_schema.md) · [Reproducibility](docs/reproducibility.md)

## Workflow

The default configuration uses 10 development sandstone rocks, 20 descriptors
and 12 random seeds per fold, giving 120 search tasks.

1. Hold out one rock and use the remaining nine for training.
2. Balance the training rocks by subvolume count. All seeds in a fold share one
   training table.
3. Fit preprocessing on the training table: base-10 logarithms for positive
   descriptors and permeability, and a scaled inverse hyperbolic sine for signed
   Euler density.
4. Run PySR with `+`, `-`, `*` and `/`, retaining the complete Pareto front.
5. Evaluate each retained expression on the held-out rock, then summarize
   equation families, descriptor frequencies and task coverage.

## Installation

The reference versions are Python 3.13.13, PySR 1.5.10 and Julia 1.12.6.
Python dependencies are pinned in `pyproject.toml`; Julia dependencies and setup
are described in [the reproducibility notes](docs/reproducibility.md).

In an environment with the reference Python version:

```bash
python -m pip install -e ".[sr]"
```

## Input

Prepare a CSV containing the development sandstone subvolumes, with `Filename`,
`rock_name`, `lithology`, `permeability` and the 20 descriptor columns. Permeability
is in m²; descriptor units and quality checks are listed in
[the input schema](docs/input_schema.md). Keep independent-test rocks in a
separate table.

The optional `scripts/prepare_discovery_input.py` helper merges the original
`train` and `internal_test` tables with their metadata. Its usage is included in
the input schema.

## Run

Validate the input and prepare shared fold tables:

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --dry-run
```

Start the search:

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --workers 8
```

`--workers` sets the number of concurrent tasks; each PySR task runs serially.
The default `configs/sandstone_lopo.json` specifies 500 iterations, maximum
complexity 15, 30 populations of 50 expressions and parsimony 0.001.

Repeat the command to resume; verified completed tasks are skipped. Use a new
output directory when the input, configuration, code or environment changes.
On Windows, use a short output path for Julia/PySR checkpoint files.

## Outputs

Each run saves its configuration and environment metadata, shared training
tables, raw PySR artifacts, complete Pareto records and held-out metrics.
Complete runs also produce descriptor-frequency and equation-family summaries.
Generated files are excluded from Git.

To rebuild summaries from a completed run:

```bash
python scripts/analyze_formula_families.py --input-dir results/sandstone_lopo --output-dir results/sandstone_summaries
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests use synthetic inputs to check rock-level splitting, shared sampling,
preprocessing, Pareto retention, resuming and aggregation. They run without the
study data or Julia.

## Citation and license

Cranmer, M. (2023). *Interpretable machine learning for science with PySR and
SymbolicRegression.jl*. https://doi.org/10.48550/arXiv.2305.01582

Code is distributed under the [MIT license](LICENSE).
