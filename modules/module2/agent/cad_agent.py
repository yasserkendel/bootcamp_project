"""
module2/agent/cad_agent.py
"""

from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import Any, TypedDict

from modules.module2.generators.dxf_generator import DXFGenerator
from modules.module2.generators.ifc_generator import IFCGenerator

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    specs: dict[str, Any]
    cad_outputs: dict[str, str]
    cad_errors: list[str]
    video_output: str
    sourcing_results: list[dict]
    tco_output: dict
    business_plan_output: dict
    catalogue_output: dict


# ── Adaptateur Format Module 1 → Format Générateurs ──────────────────────────

def _parse_num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"[\d.]+", value)
        if m:
            return float(m.group())
    return default


def adapt_specs(raw: dict[str, Any]) -> dict[str, Any]:
    # Déjà dans le bon format → on ne touche rien
    if "dimensions" in raw and "part" in raw:
        return raw

    # Format plat Module 1 → conversion
    dn  = _parse_num(raw.get("diametre_nominal", "100"), 100.0)
    pn  = _parse_num(raw.get("pression_nominale", "40"), 40.0)
    f2f = _parse_num(raw.get("longueur_face_a_face", "229"), 229.0)

    mat = raw.get("materiau", {})
    if isinstance(mat, dict):
        body_mat = mat.get("corps", "Fonte GS 400-15")
        stem_mat = mat.get("tige",  "Inox 316")
        seat_mat = mat.get("siège", "PTFE")
        gasket   = mat.get("joint", "EPDM")
    else:
        body_mat = stem_mat = str(mat)
        seat_mat = "PTFE"
        gasket   = "EPDM"

    norme = raw.get("norme", {})
    standard = norme.get("fabrication", "EN 593") if isinstance(norme, dict) else str(norme)

    return {
        "part": {
            "reference":         f"VB-DN{int(dn)}-PN{int(pn)}",
            "name":              f"Vanne Papillon DN{int(dn)} PN{int(pn)}",
            "type":              "BUTTERFLY",
            "standard":          standard,
            "quantity_required": 200,
        },
        "dimensions": {
            "nominal_diameter_mm":     dn,
            "face_to_face_mm":         f2f,
            "flange_od_mm":            dn * 2.2,
            "bore_diameter_mm":        dn,
            "bolt_circle_diameter_mm": dn * 1.7,
            "bolt_hole_diameter_mm":   dn * 0.12,
            "bolt_holes":              8 if dn >= 100 else 4,
            "flange_thickness_mm":     dn * 0.18,
            "body_height_mm":          dn * 1.8,
            "wall_thickness_mm":       dn * 0.15,
            "stem_diameter_mm":        dn * 0.18,
        },
        "mechanical": {
            "nominal_pressure_bar": pn,
            "test_pressure_bar":    pn * 1.5,
            "max_temperature_c":    120,
            "min_temperature_c":    -10,
        },
        "materials": {
            "body":    body_mat,
            "stem":    stem_mat,
            "seat":    seat_mat,
            "gasket":  gasket,
            "bolting": "Acier inox A4-70",
        },
        "tolerances": {
            "bore_diameter":   "H7",
            "face_to_face":    "±1 mm",
            "flange_flatness": "0.1 mm",
        },
        "surface_finish": {
            "internal_roughness_ra": 3.2,
            "flange_face":           "Face plane lisse (FF)",
        },
    }

# ─────────────────────────────────────────────────────────────────────────────


def run_cad_generation(state: PipelineState) -> PipelineState:
    logger.info("[Module 2] Starting CAD generation")
    specs = state.get("specs")
    if not specs:
        return {**state, "cad_errors": ["No specs in state"]}

    # Adapter le format si nécessaire
    specs = adapt_specs(specs)

    output_dir = Path("outputs") / specs.get("part", {}).get("reference", "unknown")
    output_dir.mkdir(parents=True, exist_ok=True)

    cad_outputs: dict[str, str] = {"dxf": "", "ifc": ""}
    cad_errors: list[str] = []

    # ── DXF generation ───────────────────────────────────────────────────────
    try:
        dxf_gen = DXFGenerator(specs, output_dir)
        dxf_path = dxf_gen.generate()
        cad_outputs["dxf"] = str(dxf_path)
    except Exception as exc:
        cad_errors.append(f"DXF generation failed: {exc}")

    # ── IFC generation ───────────────────────────────────────────────────────
    try:
        ifc_gen = IFCGenerator(specs, output_dir)
        ifc_path = ifc_gen.generate()
        cad_outputs["ifc"] = str(ifc_path)
    except Exception as exc:
        cad_errors.append(f"IFC generation failed: {exc}")

    return {
        **state,
        "cad_outputs": cad_outputs,
        "cad_errors":  cad_errors,
    }