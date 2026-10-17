"""Ordered search inputs; physical groups do not constrain candidate generation."""

PARAM_NAMES = [
    "porosity_extracted",
    "specific_surface",
    "mean_chord_length",
    "mean_local_thickness",
    "max_local_thickness",
    "local_thickness_95th",
    "mean_pore_equivalent_radius",
    "mean_throat_equivalent_radius",
    "critical_percolating_throat_radius",
    "formation_factor",
    "electrical_path_tortuosity",
    "geometric_tortuosity",
    "largest_connected_pore_fraction",
    "euler_density",
    "mean_coordination_number",
    "median_throat_length_to_diameter",
    "s2_short_integral",
    "s2_mid_integral",
    "s2_long_integral",
    "pore_phase_fractal_dimension",
]
POSITIVE_FEATURES = [name for name in PARAM_NAMES if name != "euler_density"]
DEVELOPMENT_ROCKS = (
    "Bandera Brown",
    "Berea",
    "Berea Upper Gray",
    "Buff Berea",
    "Castle Gate",
    "Kirby",
    "Leopard",
    "Parker",
    "Zebra A",
    "Zebra B",
)
SEALED_ROCKS = frozenset({"Bandera Gray A", "Bandera Gray B"})
DESCRIPTOR_VERSION = "existing_canonical_20260727_user_validated"
LENGTH_DESCRIPTORS = frozenset(
    {
        "mean_chord_length",
        "mean_local_thickness",
        "max_local_thickness",
        "local_thickness_95th",
        "mean_pore_equivalent_radius",
        "mean_throat_equivalent_radius",
        "critical_percolating_throat_radius",
        "s2_short_integral",
        "s2_mid_integral",
        "s2_long_integral",
    }
)
# Reporting units describe the supplied numeric table, not search constraints.
UNITS = {name: "1" for name in PARAM_NAMES}
UNITS.update({name: "um" for name in LENGTH_DESCRIPTORS})
UNITS.update(specific_surface="um^-1", euler_density="um^-3", permeability="m^2")
