# Input schema

Provide one CSV of development sandstone subvolumes. No example observations or
research values are shipped. Column names are exact; legacy aliases are not
silently substituted because some older names describe different quantities.

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

`resolution_um` and other audit columns may be retained but are not search inputs.
No standardization, imputation or further unit conversion is performed.

The default rock set is Bandera Brown, Berea, Berea Upper Gray, Buff Berea,
Castle Gate, Kirby, Leopard, Parker, Zebra A and Zebra B. Bandera Gray A and
Bandera Gray B are independent hold-out rocks and are rejected before numerical
quality control. All other rock sets require an explicit separate configuration.
Carbonates are not supported by this release.

Missing or duplicate IDs, missing grouping information, a wrong lithology or an
unexpected rock set are errors. Numerical quality control excludes nonfinite
rows, nonpositive permeability and nonpositive values among the 19 positive
descriptors. Euler density may be zero or negative. Removing an entire rock by
quality control is an error. A training table with only zero Euler values is also
an error because its reference scale is undefined.

For each training fold, the nonzero absolute Euler densities in its shared
balanced table define a median scale. That same scale is applied unchanged to
the held-out rock. Test rows are not resampled. Reporting units are metadata;
they are not dimensional constraints supplied to PySR.
