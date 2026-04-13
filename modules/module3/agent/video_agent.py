"""
module3/agent/video_agent.py

LangGraph node for Module 3 — HD Presentation Video Generation.

Reads `cad_outputs` and `specs` from the shared pipeline state,
picks the best available renderer (Blender → Manim → Pillow fallback),
and writes `video_output` back to the state.

Renderer priority:
  1. Blender  — photorealistic 3D render from the IFC file (best quality)
  2. Manim    — programmatic technical animation (good quality, pure Python)
  3. Pillow   — frame-by-frame PNG → MP4 via imageio (always available fallback)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# Shared LangGraph pipeline state
# (keep in sync with module2/agent/cad_agent.py)
# ─────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    specs:                dict[str, Any]
    cad_outputs:          dict[str, str]
    cad_errors:           list[str]
    video_output:         str           # written by this module
    video_renderer_used:  str           # "blender" | "manim" | "pillow"
    video_errors:         list[str]
    sourcing_results:     list[dict]
    tco_output:           dict
    business_plan_output: dict
    catalogue_output:     dict


# ─────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────

def run_video_generation(state: PipelineState) -> PipelineState:
    """
    LangGraph node entry point.

    Graph wiring:
        graph.add_node("module3_video", run_video_generation)
        graph.add_edge("module2_cad", "module3_video")
        graph.add_edge("module3_video", "module4_sourcing")
    """
    logger.info("[Module 3] Starting video generation")

    specs       = state.get("specs")
    cad_outputs = state.get("cad_outputs", {})

    if not specs:
        return {**state, "video_errors": ["No specs in state — Module 1 may have failed"]}

    ifc_path = cad_outputs.get("ifc", "")
    dxf_path = cad_outputs.get("dxf", "")

    output_dir = Path("outputs") / specs.get("part", {}).get("reference", "unknown")
    output_dir.mkdir(parents=True, exist_ok=True)

    video_errors: list[str] = []

    # ── Try each renderer in priority order ──────
    renderer_used, video_path = _render_with_best_available(
        specs=specs,
        ifc_path=ifc_path,
        dxf_path=dxf_path,
        output_dir=output_dir,
        errors=video_errors,
    )

    if video_path is None:
        return {
            **state,
            "video_errors": video_errors,
            "video_output": "",
            "video_renderer_used": "none",
        }

    logger.info("[Module 3] Video generated via %s: %s", renderer_used, video_path)
    return {
        **state,
        "video_output":        str(video_path),
        "video_renderer_used": renderer_used,
        "video_errors":        video_errors,
    }


def _render_with_best_available(
    specs: dict,
    ifc_path: str,
    dxf_path: str,
    output_dir: Path,
    errors: list[str],
) -> tuple[str, Path | None]:
    # module3/agent/video_agent.py
    try:
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(specs, ifc_path, output_dir)
        if r.is_available():
            path = r.render()
            return "blender", path
        else:
            # IMPROVED LOGGING:
            import os
            bp = os.environ.get("BLENDER_PATH", "NOT SET")
            logger.warning("[Module 3] Blender not found. BLENDER_PATH is currently: %s", bp)

    except Exception as exc:
        msg = f"Blender renderer failed: {exc}"
        logger.warning("[Module 3] %s", msg)
        errors.append(msg)

    # 2. Manim
    try:
        from module3.renderer.manim_renderer import ManimRenderer
        r = ManimRenderer(specs, output_dir)
        if r.is_available():
            path = r.render()
            return "manim", path
        else:
            logger.info("[Module 3] Manim not found, falling back to Pillow")
    except Exception as exc:
        msg = f"Manim renderer failed: {exc}"
        logger.warning("[Module 3] %s", msg)
        errors.append(msg)

    # 3. Pillow fallback (always available)
    try:
        from module3.renderer.pillow_renderer import PillowRenderer
        r = PillowRenderer(specs, output_dir)
        path = r.render()
        return "pillow", path
    except Exception as exc:
        msg = f"Pillow fallback renderer failed: {exc}"
        logger.error("[Module 3] %s", msg)
        errors.append(msg)

    return "none", None


# ─────────────────────────────────────────────────
# Standalone runner
# ─────────────────────────────────────────────────

def run_standalone(state_path: str | Path) -> dict[str, Any]:
    """Run Module 3 without the full LangGraph pipeline."""
    with open(state_path) as f:
        state: PipelineState = json.load(f)
    return run_video_generation(state)
