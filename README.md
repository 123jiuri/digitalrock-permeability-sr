# Symbolic Regression for Digital-Rock Permeability

This repository contains the reusable symbolic-regression workflow for searching interpretable permeability equations from pore-scale digital-rock descriptors.

**Code only:** no digital-rock images, descriptor tables, permeability labels, manuscript figures, or private result archives are included.

## Workflow

```text
CSV descriptor table
        |
        v
20 canonical descriptors + log transforms
        |
        v
Repeated PySR searches with independent seeds
        |
        v
Pareto equations and canonical formula families
        |
        v
Consensus-family and descriptor-level analysis
```

The workflow distinguishes an individual high-scoring equation from a reproducible low-complexity formula family. It does not claim that one equation is a universal permeability law.

## Installation

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[sr]"
```

PySR also requires a Julia runtime and Julia dependencies. Follow the [PySR installation guide](https://astroautomata.com/PySR/latest/installation/) for the platform-specific setup.

For formula-family post-processing without PySR:

```bash
python -m pip install -e "."
```

## Input CSV

The CSV must contain `permeability` and these 20 canonical descriptor columns:

```text
porosity_extracted
specific_surface
mean_chord_length
mean_local_thickness
max_local_thickness
local_thickness_95th
mean_pore_equivalent_radius
mean_throat_equivalent_radius
critical_percolating_throat_radius
formation_factor
electrical_path_tortuosity
geometric_tortuosity
largest_connected_pore_fraction
euler_density
mean_coordination_number
median_throat_length_to_diameter
s2_short_integral
s2_mid_integral
s2_long_integral
pore_phase_fractal_dimension
```

`permeability` and the 19 positive descriptors must be finite and positive. `euler_density` may retain either sign. The target and positive descriptors use `log10`; `euler_density` uses a signed `asinh` transform whose scale is estimated from the training CSV. `examples/descriptor_schema.csv` is a header-only schema file and contains no research data.

## Run symbolic regression

Smoke test:

```bash
python scripts/run_symbolic_regression.py \
  --train-csv path/to/train.csv \
  --output-dir results/smoke \
  --seeds 41 \
  --iterations 10 \
  --populations 2 \
  --population-size 20 \
  --maxsize 7
```

Formal multi-seed configuration:

```bash
python scripts/run_symbolic_regression.py \
  --train-csv path/to/train.csv \
  --internal-csv path/to/internal.csv \
  --external-csv path/to/external.csv \
  --output-dir results/formal \
  --seeds 41 42 43 123 456 789 1111 2222 3333 4444 5555 6666 \
  --iterations 500 \
  --populations 30 \
  --population-size 50 \
  --maxsize 15
```

Each run records equations, per-seed summaries, descriptor frequencies, formula-family summaries, search configuration, preprocessing metadata, software versions, system information, and a log. Result directories are ignored by Git.

## Analyze formula families

```bash
python scripts/analyze_formula_families.py \
  --input-dir results/formal \
  --output-dir results/family_analysis \
  --lithology sandstone
```

The analyzer groups equations by rounded SymPy canonical forms and reports descriptor classes, seed coverage, complexity, and available train/internal/external metrics.

## Reproducibility and scope

- Input paths are command-line arguments; there is no project-local data assumption.
- Search seeds, transformations, model settings, package versions, and system information are saved in `metadata.json`.
- The default search is deterministic and serial, matching the formal study configuration.
- The code package is intended to reproduce the computational workflow when the corresponding descriptor tables are supplied separately.
- Data, results, and private metadata are deliberately excluded from the repository.
