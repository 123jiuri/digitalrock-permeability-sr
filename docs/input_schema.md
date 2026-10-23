# Input schema

Provide one CSV of development sandstone subvolumes using the column names and
reporting units below.

| Column | Meaning or reporting unit |
|---|---|
| `Filename` | Unique subvolume ID; a raw file is not opened |
| `rock_name` | Source rock name; the LOPO grouping unit |
| `lithology` | Must be `sandstone` |
| `permeability` | Physical intrinsic permeability in m², already restored from source voxel normalization |
| `porosity_extracted` | Dimensionless |
| `specific_surface` | µm⁻¹; interface area per bulk volume |
| `mean_chord_length` | µm |
| `mean_local_thickness` | µm |
| `max_local_thickness` | µm |
| `local_thickness_95th` | µm |
| `mean_pore_equivalent_radius` | µm |
| `mean_throat_equivalent_radius` | µm |
| `critical_percolating_throat_radius` | µm; inlet-to-outlet percolation threshold |
| `formation_factor` | Dimensionless |
| `electrical_path_tortuosity` | Dimensionless |
| `geometric_tortuosity` | Dimensionless local throat elongation, not bulk hydraulic tortuosity |
| `largest_connected_pore_fraction` | Dimensionless |
| `euler_density` | µm⁻³; signed values retained |
| `mean_coordination_number` | Dimensionless |
| `median_throat_length_to_diameter` | Dimensionless |
| `s2_short_integral` | µm, using physical lag distances |
| `s2_mid_integral` | µm, using physical lag distances |
| `s2_long_integral` | µm, using physical lag distances |
| `pore_phase_fractal_dimension` | Dimensionless |

`resolution_um` and other audit columns may be retained alongside the search
inputs. Supply values in the listed units; the pipeline applies logarithmic and
scaled-asinh transformations directly, without standardization or imputation.

The default rock set is Bandera Brown, Berea, Berea Upper Gray, Buff Berea,
Castle Gate, Kirby, Leopard, Parker, Zebra A and Zebra B. Keep Bandera Gray A and
Bandera Gray B in the separate independent-test set. The runner validates rock
membership before numerical quality control; a different development rock set
requires a separate configuration.

IDs must be unique, grouping information complete, and lithology and rock names
consistent with the configuration. Numerical quality control retains finite
rows with positive permeability and positive values for the 19 positive
descriptors. Euler density may be zero or negative. Each rock must retain valid
subvolumes, and each balanced training table needs nonzero Euler values to
define the transformation scale.

For each training fold, the nonzero absolute Euler densities in its shared
balanced table define a median scale. That same scale is applied unchanged to
the complete held-out rock. Units document the input values; dimensional
interpretation follows the search.

## Optional input merger

For the original two-root archive layout:

```bash
python scripts/prepare_discovery_input.py --numeric-root /path/to/numeric_tables --metadata-root /path/to/metadata_tables --output /path/to/local/discovery.csv
```

Both roots contain `sandstone/train/complete_features.csv` and
`sandstone/internal_test/complete_features.csv`. The helper joins numeric values
and metadata by subvolume ID, checks one-to-one matches and writes the merged
development table. Already merged CSV inputs can be used directly. Descriptor
extraction and physical-unit restoration precede this step.
