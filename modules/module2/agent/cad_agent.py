"""
module2/agent/cad_agent.py
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, TypedDict

from module2.generators.dxf_generator import DXFGenerator
from module2.generators.ifc_generator import IFCGenerator

logger = logging.getLogger(__name__)

class PipelineState(TypedDict, total=False):
    """
    Shared state that flows through the full LangGraph pipeline.
    """
    specs: dict[str, Any]
    cad_outputs: dict[str, str] 
    cad_errors: list[str]
    video_output: str
    sourcing_results: list[dict]
    tco_output: dict
    business_plan_output: dict
    catalogue_output: dict

def run_cad_generation(state: PipelineState) -> PipelineState:
    logger.info("[Module 2] Starting CAD generation")
    specs = state.get("specs")
    if not specs:
        return {**state, "cad_errors": ["No specs in state"]}

    output_dir = Path("outputs") / specs.get("part", {}).get("reference", "unknown")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize keys so tests always find them
    cad_outputs: dict[str, str] = {"dxf": "", "ifc": ""}
    cad_errors: list[str] = []

    # ── DXF generation ─────────────────────────
    try:
        dxf_gen = DXFGenerator(specs, output_dir)
        dxf_path = dxf_gen.generate()
        cad_outputs["dxf"] = str(dxf_path)
    except Exception as exc:
        cad_errors.append(f"DXF generation failed: {exc}")

    # ── IFC generation ─────────────────────────
    try:
        ifc_gen = IFCGenerator(specs, output_dir)
        ifc_path = ifc_gen.generate()
        cad_outputs["ifc"] = str(ifc_path)
    except Exception as exc:
        cad_errors.append(f"IFC generation failed: {exc}")

    return {
        **state,
        "cad_outputs": cad_outputs,
        "cad_errors": cad_errors,
    }
# ─────────────────────────────────────────────────
# Standalone runner for Module 2
# ─────────────────────────────────────────────────

def run_standalone(state_path: str | Path) -> dict[str, Any]:
    """Run Module 2 without the full LangGraph pipeline."""
    import json
    
    # Load the current state (usually from Module 1)
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Trigger the CAD generation logic
    # This calls the main entry point of your agent
    result = run_cad_generation(state)
    
    # Print a summary for you in the terminal
    print(f"\n✅ Module 2 Complete")
    if "cad_outputs" in result:
        print(f"   - DXF: {result['cad_outputs'].get('dxf')}")
        print(f"   - IFC: {result['cad_outputs'].get('ifc')}") # <--- Verify this line
    
    return result