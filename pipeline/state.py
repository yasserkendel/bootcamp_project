"""
pipeline/state.py

Définition de l'état partagé LangGraph pour INDUSTRIE IA.
Cet état traverse tous les modules du pipeline.
"""

from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict


class IndustrieIAState(TypedDict, total=False):
    """
    État global partagé entre tous les nœuds LangGraph.

    Chaque module lit et enrichit cet état sans écraser
    les données des modules précédents.
    """

    # ── Entrée utilisateur ─────────────────────────────────────────
    pdf_path: str                        # Chemin vers le PDF uploadé

    # ── Module 1 — Extraction ─────────────────────────────────────
    extracted_text: str                  # Texte brut extrait du PDF
    specs: dict[str, Any]               # JSON structuré des spécifications
    module1_status: str                  # "success" | "error"
    module1_error: Optional[str]         # Message d'erreur si échec

    # ── Module 2 — Génération CAD ─────────────────────────────────
    cad_outputs: dict[str, str]          # {"dxf": "/path/...", "ifc": "/path/..."}
    cad_errors: list[str]                # Erreurs non-bloquantes
    module2_status: str                  # "success" | "partial" | "error"

    # ── Modules futurs (placeholders) ─────────────────────────────
    video_output: Optional[str]          # Module 3
    sourcing_results: list[dict]         # Module 4
    negotiation_output: Optional[dict]   # Module 5
    tco_output: Optional[dict]           # Module 6
    business_plan_output: Optional[dict] # Module 7
    digital_twin_output: Optional[dict]  # Module 8
    catalogue_output: Optional[dict]     # Module 9

    # ── Métadonnées pipeline ───────────────────────────────────────
    pipeline_errors: list[str]           # Erreurs globales accumulées
    completed_modules: list[str]         # ["module1", "module2", ...]