"""
module3/tests/test_module3.py

Test suite for Module 3 — Video Generation.
Covers: validators, each renderer, and the LangGraph agent node.

Run:
    cd module3
    python -m pytest tests/ -v

Note: Blender and Manim tests are skipped if those tools aren't installed.
The Pillow renderer tests always run (no external tools needed).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from module3.utils.validators import validate_state
from module3.agent.video_agent import run_video_generation, PipelineState

DUMMY_STATE_PATH = (
    Path(__file__).parent.parent / "data" / "dummy" / "pipeline_state.json"
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def valid_state() -> dict:
    with open(DUMMY_STATE_PATH) as f:
        return json.load(f)


@pytest.fixture()
def valid_specs(valid_state) -> dict:
    return valid_state["specs"]


# ─────────────────────────────────────────────
# Validator tests
# ─────────────────────────────────────────────

class TestValidateState:

    def test_valid_state_returns_no_hard_errors(self, valid_state):
        errors = validate_state(valid_state)
        hard = [e for e in errors if not e.startswith("WARNING")]
        assert hard == [], f"Unexpected hard errors: {hard}"

    def test_missing_specs_returns_error(self):
        errors = validate_state({})
        assert any("specs" in e for e in errors)

    def test_missing_part_section(self, valid_state):
        import copy
        bad = copy.deepcopy(valid_state)
        del bad["specs"]["part"]
        errors = validate_state(bad)
        assert any("part" in e for e in errors)

    def test_missing_dimensions_key(self, valid_state):
        import copy
        bad = copy.deepcopy(valid_state)
        del bad["specs"]["dimensions"]["bore_diameter_mm"]
        errors = validate_state(bad)
        assert any("bore_diameter_mm" in e for e in errors)

    def test_missing_cad_outputs_is_warning_only(self, valid_state):
        import copy
        bad = copy.deepcopy(valid_state)
        del bad["cad_outputs"]
        errors = validate_state(bad)
        warnings = [e for e in errors if e.startswith("WARNING")]
        hard     = [e for e in errors if not e.startswith("WARNING")]
        assert len(warnings) >= 1
        assert hard == []

    def test_non_dict_input(self):
        errors = validate_state("bad input")
        assert len(errors) == 1


# ─────────────────────────────────────────────
# Pillow renderer tests (always available)
# ─────────────────────────────────────────────

class TestPillowRenderer:

    def test_renders_mp4(self, valid_specs, tmp_path):
        pytest.importorskip("PIL",   reason="Pillow not installed")
        pytest.importorskip("imageio", reason="imageio not installed")

        from module3.renderer.pillow_renderer import PillowRenderer
        r = PillowRenderer(valid_specs, tmp_path)
        path = r.render()
        assert path.exists()
        assert path.suffix == ".mp4"

    def test_output_filename_contains_reference(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")

        from module3.renderer.pillow_renderer import PillowRenderer
        r = PillowRenderer(valid_specs, tmp_path)
        path = r.render()
        assert valid_specs["part"]["reference"] in path.name

    def test_output_file_not_empty(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")

        from module3.renderer.pillow_renderer import PillowRenderer
        r = PillowRenderer(valid_specs, tmp_path)
        path = r.render()
        assert path.stat().st_size > 10_000, "MP4 file suspiciously small"

    def test_frame_title_returns_image(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")

        from module3.renderer.pillow_renderer import PillowRenderer, W, H
        r = PillowRenderer(valid_specs, tmp_path)
        img = r._frame_title(5, 50)
        assert img.size == (W, H)

    def test_frame_cross_section_returns_image(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")

        from module3.renderer.pillow_renderer import PillowRenderer, W, H
        r = PillowRenderer(valid_specs, tmp_path)
        img = r._frame_cross_section(25, 50)
        assert img.size == (W, H)

    def test_frame_specs_returns_image(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")

        from module3.renderer.pillow_renderer import PillowRenderer, W, H
        r = PillowRenderer(valid_specs, tmp_path)
        img = r._frame_specs(10, 50)
        assert img.size == (W, H)

    def test_frame_outro_returns_image(self, valid_specs, tmp_path):
        pytest.importorskip("PIL")

        from module3.renderer.pillow_renderer import PillowRenderer, W, H
        r = PillowRenderer(valid_specs, tmp_path)
        img = r._frame_outro(20, 50)
        assert img.size == (W, H)


# ─────────────────────────────────────────────
# Blender renderer tests (skipped if not installed)
# ─────────────────────────────────────────────

class TestBlenderRenderer:

    @pytest.fixture(autouse=True)
    def skip_if_no_blender(self, valid_specs, tmp_path):
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(valid_specs, "", tmp_path)
        if not r.is_available():
            pytest.skip("Blender not installed — skipping Blender tests")

    def test_is_available_returns_true(self, valid_specs, tmp_path):
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(valid_specs, "", tmp_path)
        assert r.is_available() is True

    def test_renders_mp4(self, valid_specs, tmp_path):
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(valid_specs, "", tmp_path)
        path = r.render()
        assert path.exists()
        assert path.suffix == ".mp4"

    def test_build_script_contains_reference(self, valid_specs, tmp_path):
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(valid_specs, "dummy.ifc", tmp_path)
        script = r._build_script(tmp_path / "out.mp4")
        assert valid_specs["part"]["reference"] in script

    def test_build_script_contains_geometry_values(self, valid_specs, tmp_path):
        from module3.renderer.blender_renderer import BlenderRenderer
        r = BlenderRenderer(valid_specs, "dummy.ifc", tmp_path)
        script = r._build_script(tmp_path / "out.mp4")
        # Script should contain converted mm→m values
        assert "0.11" in script or "0.110" in script   # flange_od * 0.75 / 2 * 0.001


# ─────────────────────────────────────────────
# Manim renderer tests (skipped if not installed)
# ─────────────────────────────────────────────

class TestManimRenderer:

    @pytest.fixture(autouse=True)
    def skip_if_no_manim(self):
        pytest.importorskip("manim", reason="Manim not installed — skipping Manim tests")

    def test_is_available_returns_true(self, valid_specs, tmp_path):
        from module3.renderer.manim_renderer import ManimRenderer
        r = ManimRenderer(valid_specs, tmp_path)
        assert r.is_available() is True

    def test_build_scene_source_contains_part_name(self, valid_specs, tmp_path):
        from module3.renderer.manim_renderer import ManimRenderer
        r = ManimRenderer(valid_specs, tmp_path)
        src = r._build_scene_source()
        assert valid_specs["part"]["name"] in src

    def test_build_scene_source_contains_dn(self, valid_specs, tmp_path):
        from module3.renderer.manim_renderer import ManimRenderer
        r = ManimRenderer(valid_specs, tmp_path)
        src = r._build_scene_source()
        assert str(valid_specs["specs"]["dimensions"]["nominal_diameter_mm"] \
                   if "specs" in valid_specs else
                   valid_specs["dimensions"]["nominal_diameter_mm"]) in src


# ─────────────────────────────────────────────
# LangGraph agent node tests
# ─────────────────────────────────────────────

class TestVideoAgent:

    def test_missing_specs_returns_error(self):
        state: PipelineState = {}
        result = run_video_generation(state)
        assert "video_errors" in result
        assert len(result["video_errors"]) > 0

    def test_agent_preserves_existing_state_keys(self, valid_state, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")
        monkeypatch.chdir(tmp_path)

        state = {**valid_state, "cad_outputs": {"dxf": "x.dxf", "ifc": "x.ifc"}}
        result = run_video_generation(state)
        # Keys from other modules must survive
        assert result.get("cad_outputs") == state["cad_outputs"]

    def test_agent_writes_video_output_key(self, valid_state, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")
        monkeypatch.chdir(tmp_path)

        result = run_video_generation({**valid_state})
        assert "video_output" in result

    def test_agent_writes_renderer_used_key(self, valid_state, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")
        monkeypatch.chdir(tmp_path)

        result = run_video_generation({**valid_state})
        assert "video_renderer_used" in result
        assert result["video_renderer_used"] in ("blender", "manim", "pillow", "none")

    def test_pillow_fallback_always_produces_file(self, valid_state, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")
        monkeypatch.chdir(tmp_path)

        # Force Blender and Manim to be unavailable
        with patch("module3.renderer.blender_renderer.BlenderRenderer.is_available",
                   return_value=False), \
             patch("module3.renderer.manim_renderer.ManimRenderer.is_available",
                   return_value=False):
            result = run_video_generation({**valid_state})

        assert result["video_renderer_used"] == "pillow"
        assert Path(result["video_output"]).exists()

    def test_agent_no_hard_errors_with_pillow(self, valid_state, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("imageio")
        monkeypatch.chdir(tmp_path)

        with patch("module3.renderer.blender_renderer.BlenderRenderer.is_available",
                   return_value=False), \
             patch("module3.renderer.manim_renderer.ManimRenderer.is_available",
                   return_value=False):
            result = run_video_generation({**valid_state})

        hard_errors = [e for e in result.get("video_errors", [])
                       if "Blender" not in e and "Manim" not in e]
        assert hard_errors == [], f"Unexpected errors: {hard_errors}"
