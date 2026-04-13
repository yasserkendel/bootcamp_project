"""
module3/utils/validators.py

Validates the incoming pipeline state for Module 3.
"""

from __future__ import annotations
from typing import Any


def validate_state(state: dict[str, Any]) -> list[str]:
    """
    Validate that the pipeline state has what Module 3 needs.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []

    if not isinstance(state, dict):
        return ["state must be a dict"]

    # specs is required
    specs = state.get("specs")
    if not specs:
        errors.append("'specs' missing from state")
        return errors

    for section in ("part", "dimensions", "mechanical", "materials"):
        if section not in specs:
            errors.append(f"specs.{section} missing")

    part = specs.get("part", {})
    for key in ("name", "reference", "standard", "quantity_required"):
        if key not in part:
            errors.append(f"specs.part.{key} missing")

    dims = specs.get("dimensions", {})
    for key in ("nominal_diameter_mm", "face_to_face_mm", "flange_od_mm",
                "body_height_mm", "bore_diameter_mm", "stem_diameter_mm",
                "flange_thickness_mm"):
        if key not in dims:
            errors.append(f"specs.dimensions.{key} missing")

    mech = specs.get("mechanical", {})
    for key in ("nominal_pressure_bar", "test_pressure_bar",
                "max_temperature_c", "min_temperature_c"):
        if key not in mech:
            errors.append(f"specs.mechanical.{key} missing")

    # cad_outputs is optional but logged if absent
    if not state.get("cad_outputs"):
        errors.append("WARNING: cad_outputs missing — Blender will have no IFC to import")

    return errors
