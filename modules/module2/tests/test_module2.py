"""
module2/tests/test_module2.py

Test suite for Module 2 — CAD Generation.
Covers: validators, DXF generation, IFC generation, and the LangGraph agent node.

Run with:
    pytest module2/tests/ -v
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from module2.utils.validators import validate_specs
from module2.generators.dxf_generator import DXFGenerator
from module2.generators.ifc_generator import IFCGenerator
from module2.agent.cad_agent import run_cad_generation, PipelineState


# ──────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────

DUMMY_SPECS_PATH = Path(__file__).parent.parent / "data" / "dummy" / "valve_dn100_pn40.json"


@pytest.fixture(scope="session")
def valid_specs() -> dict:
    with open(DUMMY_SPECS_PATH) as f:
        return json.load(f)


@pytest.fixture()
def tmp_output(tmp_path) -> Path:
    return tmp_path


# ──────────────────────────────────────────────────
# Validator tests
# ──────────────────────────────────────────────────

class TestValidateSpecs:

    def test_valid_specs_returns_no_errors(self, valid_specs):
        errors = validate_specs(valid_specs)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_missing_section_raises_error(self, valid_specs):
        bad = {k: v for k, v in valid_specs.items() if k != "dimensions"}
        errors = validate_specs(bad)
        assert any("dimensions" in e for e in errors)

    def test_missing_dimension_key(self, valid_specs):
        import copy
        bad = copy.deepcopy(valid_specs)
        del bad["dimensions"]["bore_diameter_mm"]
        errors = validate_specs(bad)
        assert any("bore_diameter_mm" in e for e in errors)

    def test_negative_dimension_fails(self, valid_specs):
        import copy
        bad = copy.deepcopy(valid_specs)
        bad["dimensions"]["nominal_diameter_mm"] = -5
        errors = validate_specs(bad)
        assert any("nominal_diameter_mm" in e for e in errors)

    def test_test_pressure_less_than_nominal_fails(self, valid_specs):
        import copy
        bad = copy.deepcopy(valid_specs)
        bad["mechanical"]["test_pressure_bar"] = 10   # less than nominal 40
        errors = validate_specs(bad)
        assert any("test_pressure_bar" in e for e in errors)

    def test_bcd_larger_than_flange_od_fails(self, valid_specs):
        import copy
        bad = copy.deepcopy(valid_specs)
        bad["dimensions"]["bolt_circle_diameter_mm"] = 9999
        errors = validate_specs(bad)
        assert any("bolt_circle_diameter_mm" in e for e in errors)

    def test_non_dict_input(self):
        errors = validate_specs("not a dict")
        assert len(errors) == 1
        assert "dict" in errors[0]


# ──────────────────────────────────────────────────
# DXF generator tests
# ──────────────────────────────────────────────────

class TestDXFGenerator:

    def test_generates_dxf_file(self, valid_specs, tmp_output):
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        assert path.exists(), f"DXF file not found at {path}"
        assert path.suffix == ".dxf"

    def test_dxf_filename_contains_reference(self, valid_specs, tmp_output):
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        assert valid_specs["part"]["reference"] in path.name

    def test_dxf_file_is_not_empty(self, valid_specs, tmp_output):
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        assert path.stat().st_size > 1024, "DXF file is suspiciously small"

    def test_dxf_is_valid_ezdxf_file(self, valid_specs, tmp_output):
        import ezdxf
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        doc = ezdxf.readfile(str(path))
        assert doc is not None

    def test_dxf_has_expected_layers(self, valid_specs, tmp_output):
        import ezdxf
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        doc = ezdxf.readfile(str(path))
        layer_names = {layer.dxf.name for layer in doc.layers}
        for expected in ("VISIBLE", "HIDDEN", "CENTER", "DIMENSION", "TEXT"):
            assert expected in layer_names, f"Layer '{expected}' missing from DXF"

    def test_dxf_modelspace_has_entities(self, valid_specs, tmp_output):
        import ezdxf
        gen = DXFGenerator(valid_specs, tmp_output)
        path = gen.generate()
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        entities = list(msp)
        assert len(entities) > 10, "DXF modelspace has too few entities"


# ──────────────────────────────────────────────────
# IFC generator tests
# ──────────────────────────────────────────────────

class TestIFCGenerator:

    def test_generates_ifc_file(self, valid_specs, tmp_output):
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        assert path.exists(), f"IFC file not found at {path}"
        assert path.suffix == ".ifc"

    def test_ifc_filename_contains_reference(self, valid_specs, tmp_output):
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        assert valid_specs["part"]["reference"] in path.name

    def test_ifc_is_valid_ifcopenshell_file(self, valid_specs, tmp_output):
        import ifcopenshell
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        model = ifcopenshell.open(str(path))
        assert model is not None

    def test_ifc_contains_flow_fittings(self, valid_specs, tmp_output):
        import ifcopenshell
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        model = ifcopenshell.open(str(path))
        fittings = model.by_type("IfcFlowFitting")
        assert len(fittings) >= 3, "Expected at least 3 IfcFlowFitting elements"

    def test_ifc_contains_property_set(self, valid_specs, tmp_output):
        import ifcopenshell
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        model = ifcopenshell.open(str(path))
        psets = model.by_type("IfcPropertySet")
        pset_names = {p.Name for p in psets}
        assert "Pset_IndustrieIA_Mechanical" in pset_names

    def test_ifc_schema_is_ifc4(self, valid_specs, tmp_output):
        import ifcopenshell
        gen = IFCGenerator(valid_specs, tmp_output)
        path = gen.generate()
        model = ifcopenshell.open(str(path))
        assert model.schema == "IFC4"


# ──────────────────────────────────────────────────
# LangGraph agent node tests
# ──────────────────────────────────────────────────

class TestCadAgent:

    def test_agent_returns_cad_outputs_keys(self, valid_specs, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state: PipelineState = {"specs": valid_specs}
        result = run_cad_generation(state)
        assert "cad_outputs" in result
        assert "dxf" in result["cad_outputs"]
        assert "ifc" in result["cad_outputs"]

    def test_agent_creates_actual_files(self, valid_specs, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state: PipelineState = {"specs": valid_specs}
        result = run_cad_generation(state)
        for fmt, path_str in result["cad_outputs"].items():
            assert Path(path_str).exists(), f"{fmt} file not found: {path_str}"

    def test_agent_with_missing_specs_returns_error(self):
        state: PipelineState = {}
        result = run_cad_generation(state)
        assert "cad_errors" in result
        assert len(result["cad_errors"]) > 0

    def test_agent_preserves_existing_state_keys(self, valid_specs, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state: PipelineState = {
            "specs": valid_specs,
            "sourcing_results": [{"mock": "data"}]
        }
        result = run_cad_generation(state)
        # State from other modules must not be lost
        assert result.get("sourcing_results") == [{"mock": "data"}]

    def test_agent_no_errors_on_valid_input(self, valid_specs, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state: PipelineState = {"specs": valid_specs}
        result = run_cad_generation(state)
        assert result.get("cad_errors", []) == [], \
            f"Unexpected errors: {result.get('cad_errors')}"
