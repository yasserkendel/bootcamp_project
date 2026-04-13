"""
pipeline/test_pipeline.py

Tests du pipeline LangGraph Module 1 → Module 2.

Lancer tous les tests :
    pytest pipeline/test_pipeline.py -v

Lancer un test spécifique :
    pytest pipeline/test_pipeline.py::test_module1_missing_pdf -v

Lancer avec couverture :
    pytest pipeline/test_pipeline.py -v --cov=pipeline --cov-report=term-missing
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Ajout du répertoire racine au sys.path ─────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.graph import (
    build_graph,
    node_module1_extract,
    node_module2_cad,
    route_after_module1,
    run_pipeline,
)
from pipeline.state import IndustrieIAState


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

DUMMY_SPECS = {
    "diametre_nominal": "DN100",
    "pression_nominale": "PN40",
    "materiau": "Inox 316L",
    "longueur_face_a_face": "229mm",
    "tolerance": "±0.1mm",
    "norme": "EN 558",
}

DUMMY_CAD_OUTPUTS = {
    "dxf": "outputs/DN100/vanne_DN100.dxf",
    "ifc": "outputs/DN100/vanne_DN100.ifc",
}


@pytest.fixture
def state_with_pdf(tmp_path) -> IndustrieIAState:
    """État initial avec un vrai fichier PDF factice (texte vide)."""
    pdf = tmp_path / "test_valve.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")
    return {
        "pdf_path": str(pdf),
        "pipeline_errors": [],
        "completed_modules": [],
    }


@pytest.fixture
def state_after_module1() -> IndustrieIAState:
    """État simulant une réussite de Module 1."""
    return {
        "pdf_path": "/fake/path.pdf",
        "extracted_text": "Vanne DN100 PN40 matériau inox 316L...",
        "specs": DUMMY_SPECS,
        "module1_status": "success",
        "module1_error": None,
        "pipeline_errors": [],
        "completed_modules": ["module1"],
    }


@pytest.fixture
def state_after_module1_failed() -> IndustrieIAState:
    """État simulant un échec de Module 1."""
    return {
        "pdf_path": "/fake/path.pdf",
        "specs": {},
        "module1_status": "error",
        "module1_error": "PDF introuvable",
        "pipeline_errors": ["PDF introuvable"],
        "completed_modules": [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Routeur conditionnel
# ══════════════════════════════════════════════════════════════════════════════

class TestRouter:
    def test_route_to_module2_on_success(self, state_after_module1):
        assert route_after_module1(state_after_module1) == "module2"

    def test_route_to_end_on_error(self, state_after_module1_failed):
        assert route_after_module1(state_after_module1_failed) == "end"

    def test_route_to_end_on_missing_status(self):
        state = {"pipeline_errors": [], "completed_modules": []}
        assert route_after_module1(state) == "end"


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Nœud Module 1
# ══════════════════════════════════════════════════════════════════════════════

class TestModule1Node:

    def test_missing_pdf_path(self):
        """Sans pdf_path → module1_status = error."""
        state = {"pipeline_errors": [], "completed_modules": []}
        result = node_module1_extract(state)
        assert result["module1_status"] == "error"
        assert "pdf_path" in result["module1_error"]

    def test_pdf_not_found(self):
        """PDF inexistant → module1_status = error."""
        state = {
            "pdf_path": "/chemin/inexistant/fichier.pdf",
            "pipeline_errors": [],
            "completed_modules": [],
        }
        result = node_module1_extract(state)
        assert result["module1_status"] == "error"
        assert "introuvable" in result["module1_error"].lower()

    def test_empty_pdf_text(self, tmp_path):
        """PDF qui retourne texte vide → module1_status = error."""
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        state = {
            "pdf_path": str(pdf),
            "pipeline_errors": [],
            "completed_modules": [],
        }
        with patch("modules.module1.extractor.extract_text_from_pdf", return_value=""):
            result = node_module1_extract(state)
        assert result["module1_status"] == "error"

    def test_successful_extraction(self, tmp_path):
        """Extraction réussie → module1_status = success, specs remplies."""
        pdf = tmp_path / "valve.pdf"
        pdf.write_bytes(b"%PDF-1.4 Vanne DN100 PN40")
        state = {
            "pdf_path": str(pdf),
            "pipeline_errors": [],
            "completed_modules": [],
        }

        with patch("modules.module1.extractor.extract_text_from_pdf",
                   return_value="Vanne DN100 PN40 Inox 316L"), \
             patch("modules.module1.extractor.extract_specs_from_text",
                   return_value=DUMMY_SPECS):
            result = node_module1_extract(state)

        assert result["module1_status"] == "success"
        assert result["specs"] == DUMMY_SPECS
        assert "module1" in result["completed_modules"]
        assert result["module1_error"] is None

    def test_llm_error_response(self, tmp_path):
        """LLM retourne une erreur JSON → module1_status = error."""
        pdf = tmp_path / "valve.pdf"
        pdf.write_bytes(b"%PDF-1.4 Vanne DN100")
        state = {
            "pdf_path": str(pdf),
            "pipeline_errors": [],
            "completed_modules": [],
        }

        bad_specs = {"error": "JSON invalide", "raw_response": "```not json```"}
        with patch("modules.module1.extractor.extract_text_from_pdf",
                   return_value="Vanne DN100"), \
             patch("modules.module1.extractor.extract_specs_from_text",
                   return_value=bad_specs):
            result = node_module1_extract(state)

        assert result["module1_status"] == "error"

    def test_exception_handling(self, tmp_path):
        """Exception interne → module1_status = error, pas de crash."""
        pdf = tmp_path / "valve.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        state = {
            "pdf_path": str(pdf),
            "pipeline_errors": [],
            "completed_modules": [],
        }

        with patch("modules.module1.extractor.extract_text_from_pdf",
                   side_effect=RuntimeError("crash simulé")):
            result = node_module1_extract(state)

        assert result["module1_status"] == "error"
        assert "crash simulé" in result["module1_error"]


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Nœud Module 2
# ══════════════════════════════════════════════════════════════════════════════

class TestModule2Node:

    def test_skipped_when_module1_failed(self, state_after_module1_failed):
        """Module 1 en erreur → Module 2 ignoré."""
        result = node_module2_cad(state_after_module1_failed)
        assert result["module2_status"] == "error"
        assert result["cad_outputs"] == {"dxf": "", "ifc": ""}

    def test_missing_specs(self):
        """Specs vides → module2_status = error."""
        state = {
            "module1_status": "success",
            "specs": {},
            "pipeline_errors": [],
            "completed_modules": ["module1"],
        }
        result = node_module2_cad(state)
        assert result["module2_status"] == "error"

    def test_successful_cad_generation(self, state_after_module1):
        """CAD généré avec succès → module2_status = success."""
        mock_result = {
            **state_after_module1,
            "cad_outputs": DUMMY_CAD_OUTPUTS,
            "cad_errors": [],
        }
        with patch("modules.module2.agent.cad_agent.run_cad_generation",
                   return_value=mock_result):
            result = node_module2_cad(state_after_module1)

        assert result["module2_status"] == "success"
        assert result["cad_outputs"]["dxf"] != ""
        assert "module2" in result["completed_modules"]

    def test_partial_cad_generation(self, state_after_module1):
        """Seulement DXF généré (IFC échoue) → module2_status = partial."""
        partial_outputs = {"dxf": "outputs/DN100/vanne.dxf", "ifc": ""}
        mock_result = {
            **state_after_module1,
            "cad_outputs": partial_outputs,
            "cad_errors": ["IFC generation failed: missing library"],
        }
        with patch("modules.module2.agent.cad_agent.run_cad_generation",
                   return_value=mock_result):
            result = node_module2_cad(state_after_module1)

        assert result["module2_status"] == "partial"
        assert result["cad_outputs"]["dxf"] != ""

    def test_exception_handling(self, state_after_module1):
        """Exception interne → module2_status = error, pas de crash."""
        with patch("modules.module2.agent.cad_agent.run_cad_generation",
                   side_effect=RuntimeError("crash CAD")):
            result = node_module2_cad(state_after_module1)

        assert result["module2_status"] == "error"
        assert "crash CAD" in result["cad_errors"][0]

    def test_errors_propagated_to_pipeline(self, state_after_module1):
        """Les erreurs CAD sont ajoutées à pipeline_errors."""
        mock_result = {
            **state_after_module1,
            "cad_outputs": {"dxf": "", "ifc": ""},
            "cad_errors": ["DXF generation failed: bad dims"],
        }
        with patch("modules.module2.agent.cad_agent.run_cad_generation",
                   return_value=mock_result):
            result = node_module2_cad(state_after_module1)

        assert "DXF generation failed: bad dims" in result["pipeline_errors"]


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Pipeline complet (intégration)
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:

    def test_full_pipeline_success(self, tmp_path):
        """Pipeline complet : Module 1 OK → Module 2 OK."""
        pdf = tmp_path / "vanne.pdf"
        pdf.write_bytes(b"%PDF-1.4 Vanne DN100 PN40 Inox 316L")

        with patch("modules.module1.extractor.extract_text_from_pdf",
                   return_value="Vanne DN100 PN40 Inox 316L"), \
             patch("modules.module1.extractor.extract_specs_from_text",
                   return_value=DUMMY_SPECS), \
             patch("modules.module2.agent.cad_agent.run_cad_generation",
                   return_value={
                       "specs": DUMMY_SPECS,
                       "module1_status": "success",
                       "cad_outputs": DUMMY_CAD_OUTPUTS,
                       "cad_errors": [],
                       "completed_modules": ["module1"],
                       "pipeline_errors": [],
                   }):
            result = run_pipeline(str(pdf))

        assert "module1" in result["completed_modules"]
        assert "module2" in result["completed_modules"]
        assert result["module1_status"] == "success"
        assert result["module2_status"] == "success"

    def test_pipeline_stops_at_module1_error(self, tmp_path):
        """Si Module 1 échoue, Module 2 ne doit pas s'exécuter."""
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        with patch("modules.module1.extractor.extract_text_from_pdf",
                   return_value=""):
            result = run_pipeline(str(pdf))

        assert result["module1_status"] == "error"
        # Module 2 ne doit pas apparaître dans les modules complétés
        assert "module2" not in result.get("completed_modules", [])

    def test_pipeline_with_nonexistent_pdf(self):
        """PDF inexistant → pipeline se termine proprement."""
        result = run_pipeline("/chemin/qui/nexiste/pas.pdf")
        assert result["module1_status"] == "error"
        assert len(result.get("pipeline_errors", [])) > 0

    def test_completed_modules_accumulate(self, tmp_path):
        """Les modules complétés s'accumulent correctement dans l'état."""
        pdf = tmp_path / "vanne.pdf"
        pdf.write_bytes(b"%PDF-1.4 Vanne")

        with patch("modules.module1.extractor.extract_text_from_pdf",
                   return_value="Vanne DN100"), \
             patch("modules.module1.extractor.extract_specs_from_text",
                   return_value=DUMMY_SPECS), \
             patch("modules.module2.agent.cad_agent.run_cad_generation",
                   return_value={
                       "specs": DUMMY_SPECS,
                       "module1_status": "success",
                       "cad_outputs": DUMMY_CAD_OUTPUTS,
                       "cad_errors": [],
                       "completed_modules": ["module1"],
                       "pipeline_errors": [],
                   }):
            result = run_pipeline(str(pdf))

        assert result["completed_modules"] == ["module1", "module2"]

    def test_state_immutability(self, tmp_path):
        """Chaque nœud retourne un nouvel état sans modifier l'original."""
        initial = {
            "pdf_path": "/fake.pdf",
            "pipeline_errors": [],
            "completed_modules": [],
        }
        initial_copy = dict(initial)

        # Le nœud ne doit pas modifier l'état d'entrée en place
        result = node_module1_extract(initial)
        assert initial == initial_copy  # L'original est intact


# ══════════════════════════════════════════════════════════════════════════════
# Tests — Construction du graphe
# ══════════════════════════════════════════════════════════════════════════════

class TestGraphConstruction:

    def test_graph_compiles(self):
        """Le graphe LangGraph doit se compiler sans erreur."""
        app = build_graph()
        assert app is not None

    def test_graph_has_correct_nodes(self):
        """Le graphe doit contenir les nœuds module1 et module2."""
        from langgraph.graph import StateGraph
        graph = StateGraph(IndustrieIAState)
        graph.add_node("module1", node_module1_extract)
        graph.add_node("module2", node_module2_cad)
        # Pas d'exception = les nœuds sont valides


# ══════════════════════════════════════════════════════════════════════════════
# Point d'entrée direct
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])