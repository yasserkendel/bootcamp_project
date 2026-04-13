"""
pipeline/graph.py

Graphe LangGraph INDUSTRIE IA — Module 1 → Module 2.

Lancer le pipeline :
    python -m pipeline.graph --pdf modules/module1/pdfs_test/vanne_industrielle_DN100.pdf

Ou depuis Python :
    from pipeline.graph import run_pipeline
    result = run_pipeline("chemin/vers/fichier.pdf")
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

# ── Ajout du répertoire racine au sys.path ─────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.state import IndustrieIAState

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


# ══════════════════════════════════════════════════════════════════════════════
# Nœud 1 — Extraction PDF (Module 1)
# ══════════════════════════════════════════════════════════════════════════════

def node_module1_extract(state: IndustrieIAState) -> IndustrieIAState:
    """
    Lit le PDF, extrait le texte et les spécifications via LLM (Mistral/Ollama).
    Entrée  : state["pdf_path"]
    Sortie  : state["specs"], state["extracted_text"], state["module1_status"]
    """
    logger.info("[Module 1] ▶ Démarrage extraction PDF")

    pdf_path = state.get("pdf_path", "")
    completed = list(state.get("completed_modules", []))
    errors = list(state.get("pipeline_errors", []))

    if not pdf_path:
        msg = "Module 1 : aucun pdf_path fourni dans l'état."
        logger.error(msg)
        return {
            **state,
            "module1_status": "error",
            "module1_error": msg,
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }

    if not Path(pdf_path).exists():
        msg = f"Module 1 : fichier PDF introuvable → {pdf_path}"
        logger.error(msg)
        return {
            **state,
            "module1_status": "error",
            "module1_error": msg,
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }

    try:
        from modules.module1.extractor import extract_text_from_pdf, extract_specs_from_text

        logger.info(f"[Module 1] Lecture du PDF : {pdf_path}")
        text = extract_text_from_pdf(pdf_path)

        if not text.strip():
            msg = "Module 1 : le PDF ne contient aucun texte extractible."
            logger.warning(msg)
            return {
                **state,
                "extracted_text": "",
                "specs": {},
                "module1_status": "error",
                "module1_error": msg,
                "pipeline_errors": errors + [msg],
                "completed_modules": completed,
            }

        logger.info("[Module 1] Analyse LLM en cours…")
        specs = extract_specs_from_text(text)

        if "error" in specs:
            msg = f"Module 1 : LLM a retourné une erreur → {specs['error']}"
            logger.warning(msg)
            return {
                **state,
                "extracted_text": text,
                "specs": specs,
                "module1_status": "error",
                "module1_error": msg,
                "pipeline_errors": errors + [msg],
                "completed_modules": completed,
            }

        logger.info(f"[Module 1] ✅ Spécifications extraites : {list(specs.keys())}")
        return {
            **state,
            "extracted_text": text,
            "specs": specs,
            "module1_status": "success",
            "module1_error": None,
            "completed_modules": completed + ["module1"],
            "pipeline_errors": errors,
        }

    except Exception as exc:
        msg = f"Module 1 : exception inattendue → {exc}"
        logger.exception(msg)
        return {
            **state,
            "module1_status": "error",
            "module1_error": msg,
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Nœud 2 — Génération CAD (Module 2)
# ══════════════════════════════════════════════════════════════════════════════

def node_module2_cad(state: IndustrieIAState) -> IndustrieIAState:
    """
    Génère les fichiers CAD (DXF + IFC) depuis les specs extraites.
    Entrée  : state["specs"]
    Sortie  : state["cad_outputs"], state["cad_errors"], state["module2_status"]
    """
    logger.info("[Module 2] ▶ Démarrage génération CAD")

    completed = list(state.get("completed_modules", []))
    errors = list(state.get("pipeline_errors", []))

    # ── Vérification que Module 1 a réussi ────────────────────────────────────
    if state.get("module1_status") != "success":
        msg = "Module 2 : ignoré car Module 1 n'a pas réussi."
        logger.warning(msg)
        return {
            **state,
            "cad_outputs": {"dxf": "", "ifc": ""},
            "cad_errors": [msg],
            "module2_status": "error",
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }

    specs = state.get("specs", {})
    if not specs:
        msg = "Module 2 : aucune specs dans l'état."
        logger.error(msg)
        return {
            **state,
            "cad_outputs": {"dxf": "", "ifc": ""},
            "cad_errors": [msg],
            "module2_status": "error",
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }

    try:
        from modules.module2.agent.cad_agent import run_cad_generation

        # run_cad_generation attend un PipelineState avec "specs"
        # On lui passe l'état courant directement (compatible TypedDict)
        cad_result = run_cad_generation(state)  # type: ignore[arg-type]

        cad_outputs = cad_result.get("cad_outputs", {"dxf": "", "ifc": ""})
        cad_errors = cad_result.get("cad_errors", [])

        # Déterminer le statut
        if not cad_errors:
            status = "success"
        elif cad_outputs.get("dxf") or cad_outputs.get("ifc"):
            status = "partial"   # Au moins un fichier généré
        else:
            status = "error"

        logger.info(f"[Module 2] ✅ Statut : {status} | Fichiers : {cad_outputs}")

        return {
            **state,
            "cad_outputs": cad_outputs,
            "cad_errors": cad_errors,
            "module2_status": status,
            "completed_modules": completed + ["module2"],
            "pipeline_errors": errors + cad_errors,
        }

    except Exception as exc:
        msg = f"Module 2 : exception inattendue → {exc}"
        logger.exception(msg)
        return {
            **state,
            "cad_outputs": {"dxf": "", "ifc": ""},
            "cad_errors": [msg],
            "module2_status": "error",
            "pipeline_errors": errors + [msg],
            "completed_modules": completed,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Routeur conditionnel — décision après Module 1
# ══════════════════════════════════════════════════════════════════════════════

def route_after_module1(state: IndustrieIAState) -> str:
    """
    Si Module 1 a réussi → aller à Module 2.
    Sinon → terminer le pipeline avec une erreur.
    """
    if state.get("module1_status") == "success":
        logger.info("[Router] Module 1 OK → Module 2")
        return "module2"
    else:
        logger.warning("[Router] Module 1 KO → Fin du pipeline")
        return "end"


# ══════════════════════════════════════════════════════════════════════════════
# Construction du graphe LangGraph
# ══════════════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Construit et compile le graphe LangGraph.

    Topologie actuelle :
        START → module1 → [conditionnel] → module2 → END
                                        └─ (erreur) → END
    """
    graph = StateGraph(IndustrieIAState)

    # ── Enregistrement des nœuds ──────────────────────────────────────────────
    graph.add_node("module1", node_module1_extract)
    graph.add_node("module2", node_module2_cad)

    # ── Point d'entrée ────────────────────────────────────────────────────────
    graph.set_entry_point("module1")

    # ── Transition conditionnelle Module 1 → Module 2 ou END ──────────────────
    graph.add_conditional_edges(
        "module1",
        route_after_module1,
        {
            "module2": "module2",
            "end": END,
        },
    )

    # ── Module 2 → FIN ────────────────────────────────────────────────────────
    graph.add_edge("module2", END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════════════════════
# Fonction publique d'exécution
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(pdf_path: str) -> IndustrieIAState:
    """
    Lance le pipeline complet depuis un chemin PDF.

    Args:
        pdf_path: Chemin absolu ou relatif vers le fichier PDF.

    Returns:
        L'état final du pipeline (dict IndustrieIAState).
    """
    app = build_graph()

    initial_state: IndustrieIAState = {
        "pdf_path": str(pdf_path),
        "pipeline_errors": [],
        "completed_modules": [],
    }

    logger.info(f"\n{'='*60}")
    logger.info("  INDUSTRIE IA — Pipeline Module 1 → Module 2")
    logger.info(f"{'='*60}")
    logger.info(f"  PDF : {pdf_path}")
    logger.info(f"{'='*60}\n")

    final_state = app.invoke(initial_state)
    return final_state


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="INDUSTRIE IA — Pipeline LangGraph Module 1 → Module 2"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Chemin vers le PDF à analyser (ex: modules/module1/pdfs_test/vanne_industrielle_DN100.pdf)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Sauvegarder le résultat final en JSON (ex: result.json)",
    )
    args = parser.parse_args()

    result = run_pipeline(args.pdf)

    # ── Affichage du résumé ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  RÉSULTAT FINAL DU PIPELINE")
    print("="*60)

    print(f"\n📋 Modules complétés : {result.get('completed_modules', [])}")
    print(f"🔴 Erreurs pipeline  : {result.get('pipeline_errors', [])}")

    specs = result.get("specs", {})
    if specs and "error" not in specs:
        print(f"\n✅ Module 1 — Spécifications extraites :")
        for k, v in specs.items():
            print(f"   {k:30s} : {v}")

    cad = result.get("cad_outputs", {})
    if cad:
        print(f"\n✅ Module 2 — Fichiers CAD générés :")
        for fmt, path in cad.items():
            if path:
                size_kb = Path(path).stat().st_size / 1024 if Path(path).exists() else 0
                print(f"   [{fmt.upper():>4}]  {path}  ({size_kb:.1f} KB)")

    cad_errors = result.get("cad_errors", [])
    if cad_errors:
        print(f"\n⚠️  Erreurs CAD :")
        for e in cad_errors:
            print(f"   • {e}")

    # ── Sauvegarde optionnelle ────────────────────────────────────────────────
    if args.output:
        # Retirer les champs non-sérialisables si besoin
        serializable = {
            k: v for k, v in result.items()
            if k != "extracted_text"  # Trop volumineux pour le résumé
        }
        Path(args.output).write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n💾 Résultat sauvegardé → {args.output}")

    print()
    sys.exit(0 if not result.get("pipeline_errors") else 1)