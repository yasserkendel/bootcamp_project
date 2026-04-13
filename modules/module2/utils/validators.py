"""
module2/utils/validators.py

Validates the incoming specs JSON from Module 1.
Returns a list of error strings (empty = valid).
"""

from __future__ import annotations
from typing import Any


REQUIRED_DIMENSION_KEYS = [
    "nominal_diameter_mm",
    "face_to_face_mm",
    "flange_od_mm",
    "flange_thickness_mm",
    "body_height_mm",
    "bolt_circle_diameter_mm",
    "bolt_holes",
    "bolt_hole_diameter_mm",
    "wall_thickness_mm",
    "bore_diameter_mm",
    "stem_diameter_mm",
]

REQUIRED_MECHANICAL_KEYS = [
    "nominal_pressure_bar",
    "test_pressure_bar",
    "max_temperature_c",
    "min_temperature_c",
]

REQUIRED_MATERIAL_KEYS = [
    "body",
    "stem",
    "seat",
    "gasket",
]


def validate_specs(specs: dict[str, Any]) -> list[str]:
    """
    Validate the specs dict. Returns a list of human-readable error messages.
    An empty list means the specs are valid.
    """
    errors: list[str] = []

    if not isinstance(specs, dict):
        return ["specs must be a dict — got: " + type(specs).__name__]

    # Top-level sections
    for section in ("dimensions", "mechanical", "materials", "part"):
        if section not in specs:
            errors.append(f"Missing required section: '{section}'")

    dims = specs.get("dimensions", {})
    for key in REQUIRED_DIMENSION_KEYS:
        if key not in dims:
            errors.append(f"dimensions.{key} is missing")
        elif not isinstance(dims[key], (int, float)):
            errors.append(f"dimensions.{key} must be numeric — got: {type(dims[key]).__name__}")
        elif dims[key] <= 0:
            errors.append(f"dimensions.{key} must be > 0 — got: {dims[key]}")

    mech = specs.get("mechanical", {})
    for key in REQUIRED_MECHANICAL_KEYS:
        if key not in mech:
            errors.append(f"mechanical.{key} is missing")

    if "nominal_pressure_bar" in mech and "test_pressure_bar" in mech:
        if mech["test_pressure_bar"] <= mech["nominal_pressure_bar"]:
            errors.append(
                f"test_pressure_bar ({mech['test_pressure_bar']}) should be "
                f"> nominal_pressure_bar ({mech['nominal_pressure_bar']})"
            )

    mats = specs.get("materials", {})
    for key in REQUIRED_MATERIAL_KEYS:
        if key not in mats:
            errors.append(f"materials.{key} is missing")

    # Geometric consistency checks
    if dims:
        bcd = dims.get("bolt_circle_diameter_mm", 0)
        flange_od = dims.get("flange_od_mm", 0)
        bore = dims.get("bore_diameter_mm", 0)
        f2f = dims.get("face_to_face_mm", 0)
        body_h = dims.get("body_height_mm", 0)

        if bcd >= flange_od:
            errors.append(
                f"bolt_circle_diameter_mm ({bcd}) must be < flange_od_mm ({flange_od})"
            )
        if bore >= flange_od:
            errors.append(
                f"bore_diameter_mm ({bore}) must be < flange_od_mm ({flange_od})"
            )
        if f2f < body_h * 0.5:
            errors.append(
                f"face_to_face_mm ({f2f}) seems too small relative to body_height_mm ({body_h})"
            )

    return errors
