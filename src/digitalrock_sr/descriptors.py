"""Canonical descriptor names and functional classes used by the study."""

from __future__ import annotations

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

DESCRIPTOR_CLASSES = {
    "volumetric_interfacial": {"porosity_extracted", "specific_surface"},
    "characteristic_geometric": {
        "mean_chord_length", "mean_local_thickness", "max_local_thickness",
        "local_thickness_95th", "mean_pore_equivalent_radius",
        "mean_throat_equivalent_radius", "critical_percolating_throat_radius",
    },
    "connectivity_transport": {
        "formation_factor", "electrical_path_tortuosity", "geometric_tortuosity",
        "largest_connected_pore_fraction", "euler_density", "mean_coordination_number",
        "median_throat_length_to_diameter",
    },
    "spatial_organization_complexity": {
        "s2_short_integral", "s2_mid_integral", "s2_long_integral",
        "pore_phase_fractal_dimension",
    },
}

POSITIVE_FEATURES = [name for name in PARAM_NAMES if name != "euler_density"]


def descriptor_class(name: str) -> str:
    for class_name, members in DESCRIPTOR_CLASSES.items():
        if name in members:
            return class_name
    return "unknown"
