"""
pipeline/graph.py — INDUSTRIE IA
Topologie complète :
  START → module1 → module2 → module4 → module5_negotiate
        → module5_listen → module5_parse
        → module6_tco → module7_business_plan → module9_catalogue → END
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from langgraph.graph import END, StateGraph

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.state import IndustrieIAState

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%H:%M:%S")

MODULES_45_DIR = ROOT / "modules" / "module4_5"


# ── Utilitaire : extraire la liste de fournisseurs depuis le state ────────────

def _resolve_suppliers(state: IndustrieIAState) -> list[dict]:
    """
    Construit la liste de fournisseurs à partir des sources disponibles,
    par ordre de priorité :
      1. final_offers  (M5 — offres négociées, contient unit_price)
      2. sourcing_results["suppliers"]  (M4 — liste brute)
    Normalise la clé prix vers 'prix_unitaire' (attendue par M6/M7/M9).
    """
    # Priorité 1 : offres finales de M5
    final_offers = state.get("final_offers", [])
    if final_offers:
        suppliers = []
        for o in final_offers:
            suppliers.append({
                "nom_fournisseur": o.get("supplier", o.get("nom_fournisseur", "Inconnu")),
                "pays": "Algérie",
                "email":  o.get("email", ""),
                "prix_unitaire": float(o.get("unit_price", o.get("prix_unitaire", 12500))),
                "delai_livraison": o.get("delai_livraison", o.get("delai", "N/A")),
            })
        return suppliers

    # Priorité 2 : fournisseurs sourcés en M4
    sourcing = state.get("sourcing_results", {})
    raw = sourcing.get("suppliers", [])
    if raw:
        suppliers = []
        for s in raw:
            sup = dict(s)
            sup["pays"] = "Algérie"
            # Normaliser la clé prix si nécessaire
            if "prix_unitaire" not in sup:
                sup["prix_unitaire"] = float(sup.get("unit_price", sup.get("prix", 12500)))
            else:
                sup["prix_unitaire"] = float(sup["prix_unitaire"])
            suppliers.append(sup)
        return suppliers

    return []


# ── Module 1 — Extraction PDF ─────────────────────────────────────────────────

def node_module1_extract(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 1] ▶ Extraction PDF")
    pdf_path  = state.get("pdf_path", "")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))

    if not pdf_path or not Path(pdf_path).exists():
        msg = f"Module 1 : PDF introuvable → {pdf_path}"
        return {**state, "module1_status": "error", "module1_error": msg,
                "pipeline_errors": errors + [msg], "completed_modules": completed}
    try:
        from modules.module1.extractor import extract_text_from_pdf, extract_specs_from_text
        text  = extract_text_from_pdf(pdf_path)
        if not text.strip():
            msg = "Module 1 : aucun texte dans le PDF."
            return {**state, "extracted_text": "", "specs": {}, "module1_status": "error",
                    "module1_error": msg, "pipeline_errors": errors + [msg], "completed_modules": completed}
        specs = extract_specs_from_text(text)
        if "error" in specs:
            msg = f"Module 1 : LLM error → {specs['error']}"
            return {**state, "extracted_text": text, "specs": specs, "module1_status": "error",
                    "module1_error": msg, "pipeline_errors": errors + [msg], "completed_modules": completed}
        logger.info(f"[Module 1] ✅ {list(specs.keys())}")
        return {**state, "extracted_text": text, "specs": specs, "module1_status": "success",
                "module1_error": None, "completed_modules": completed + ["module1"], "pipeline_errors": errors}
    except Exception as exc:
        msg = f"Module 1 : exception → {exc}"
        logger.exception(msg)
        return {**state, "module1_status": "error", "module1_error": msg,
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 2 — Génération CAD ─────────────────────────────────────────────────

def node_module2_cad(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 2] ▶ Génération CAD")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))

    if state.get("module1_status") != "success" or not state.get("specs"):
        msg = "Module 2 : ignoré (Module 1 non réussi ou specs vides)."
        return {**state, "cad_outputs": {"dxf": "", "ifc": ""}, "cad_errors": [msg],
                "module2_status": "error", "pipeline_errors": errors + [msg], "completed_modules": completed}
    try:
        from modules.module2.agent.cad_agent import run_cad_generation
        cad_result  = run_cad_generation(state)
        cad_outputs = cad_result.get("cad_outputs", {"dxf": "", "ifc": ""})
        cad_errors  = cad_result.get("cad_errors", [])
        status = "success" if not cad_errors else ("partial" if any(cad_outputs.values()) else "error")
        logger.info(f"[Module 2] ✅ {status}")
        return {**state, "cad_outputs": cad_outputs, "cad_errors": cad_errors,
                "module2_status": status, "completed_modules": completed + ["module2"],
                "pipeline_errors": errors + cad_errors}
    except Exception as exc:
        msg = f"Module 2 : exception → {exc}"
        logger.exception(msg)
        return {**state, "cad_outputs": {"dxf": "", "ifc": ""}, "cad_errors": [msg],
                "module2_status": "error", "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 4 — Sourcing Wikidata + World Bank ─────────────────────────────────

def node_module4_sourcing(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 4] ▶ Sourcing fournisseurs")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(MODULES_45_DIR))
        from sourcing_engine import search_algerian_suppliers
        from market_analyst  import get_algerian_market_data

        suppliers = search_algerian_suppliers()
        inflation = get_algerian_market_data()
        sourcing  = {"suppliers": suppliers, "inflation_rate": round(float(inflation), 2)}

        logger.info(f"[Module 4] ✅ {len(suppliers)} fournisseurs | {inflation:.2f}%")
        return {**state, "sourcing_results": sourcing, "module4_status": "success",
                "completed_modules": completed + ["module4"], "pipeline_errors": errors}
    except Exception as exc:
        msg = f"Module 4 : exception → {exc}"
        logger.exception(msg)
        return {**state, "sourcing_results": {"suppliers": [], "inflation_rate": 4.5},
                "module4_status": "error", "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 5a — Négociation (envoi emails) ────────────────────────────────────

def node_module5_negotiate(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 5a] ▶ Génération + envoi emails")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(MODULES_45_DIR))
        from negotiator import run_integrated_system

        specs    = state.get("specs", {})
        data_dir = MODULES_45_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "extracted_specs.json").write_text(
            json.dumps({"item": specs.get("diametre_nominal", "Vanne industrielle"),
                        "quantity": "200", "specs": specs}, indent=2, ensure_ascii=False))

        run_integrated_system()

        contacted_path = data_dir / "contacted_suppliers.json"
        contacted = json.loads(contacted_path.read_text()) if contacted_path.exists() else []

        logger.info(f"[Module 5a] ✅ {len(contacted)} fournisseurs contactés")
        return {**state, "negotiation_output": {"contacted": contacted, "status": "emails_sent"},
                "module5_status": "negotiated",
                "completed_modules": completed + ["module5_negotiate"], "pipeline_errors": errors}
    except Exception as exc:
        msg = f"Module 5a : exception → {exc}"
        logger.exception(msg)
        return {**state, "negotiation_output": {"contacted": [], "status": "error"},
                "module5_status": "error", "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 5b — Listener (récupère réponses Gmail) ────────────────────────────

def node_module5_listen(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 5b] ▶ Lecture réponses Gmail")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(MODULES_45_DIR))
        from response_listener import fetch_emails
        fetch_emails()

        responses_path = MODULES_45_DIR / "data" / "supplier_responses.json"
        responses = json.loads(responses_path.read_text()) if responses_path.exists() else []

        logger.info(f"[Module 5b] ✅ {len(responses)} réponses")
        return {**state, "supplier_responses": responses, "module5_listen_status": "success",
                "completed_modules": completed + ["module5_listen"], "pipeline_errors": errors}
    except Exception as exc:
        msg = f"Module 5b : exception → {exc}"
        logger.exception(msg)
        return {**state, "supplier_responses": [], "module5_listen_status": "error",
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 5c — Parser (analyse offres avec Mistral) ─────────────────────────

def node_module5_parse(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 5c] ▶ Analyse offres fournisseurs")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(MODULES_45_DIR))
        from response_parser import parse_and_negotiate
        parse_and_negotiate()

        offers_path = MODULES_45_DIR / "data" / "final_offers_table.json"
        offers = json.loads(offers_path.read_text()) if offers_path.exists() else []

        logger.info(f"[Module 5c] ✅ {len(offers)} offres finales")
        return {**state, "final_offers": offers, "module5_status": "complete",
                "completed_modules": completed + ["module5_parse"], "pipeline_errors": errors}
    except Exception as exc:
        msg = f"Module 5c : exception → {exc}"
        logger.exception(msg)
        return {**state, "final_offers": [], "module5_status": "error",
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 6 — TCO ────────────────────────────────────────────────────────────

def node_module6_tco(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 6] ▶ Calcul TCO")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(ROOT / "modules"))
        from module_6_tco import run_module_6  # type: ignore

        # Construire l'état attendu par run_module_6
        suppliers = _resolve_suppliers(state)
        m6_input = {
            **state,
            "suppliers": suppliers,
            "quantite": 200,
            "years": 10,
        }

        m6_result = run_module_6(m6_input)

        logger.info(f"[Module 6] ✅ TCO calculé — Excel: {m6_result.get('tco_excel_path')}")
        return {
            **state,
            "suppliers":        m6_result.get("suppliers", suppliers),
            "tco":              m6_result.get("tco", {}),
            "all_tco":          m6_result.get("all_tco", []),
            "tco_excel_path":   m6_result.get("tco_excel_path", ""),
            "tco_json_path":    m6_result.get("tco_json_path", ""),
            "inflation_moyenne": m6_result.get("inflation_moyenne", 5.2),
            "module6_status":   "success",
            "module6_error":    None,
            "completed_modules": completed + ["module6"],
            "pipeline_errors":  errors,
        }
    except Exception as exc:
        msg = f"Module 6 : exception → {exc}"
        logger.exception(msg)
        return {**state, "module6_status": "error", "module6_error": msg,
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 7 — Business Plan ──────────────────────────────────────────────────

def node_module7_business_plan(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 7] ▶ Génération Business Plan")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(ROOT / "modules"))
        from module_7_business_plan import run_module_7  # type: ignore

        # run_module_7 attend : specs, suppliers, tco, all_tco
        suppliers = state.get("suppliers") or _resolve_suppliers(state)
        m7_input = {
            **state,
            "suppliers": suppliers,
        }

        m7_result = run_module_7(m7_input)

        # Extraire le SWOT du meilleur fournisseur pour M9
        suppliers_bp = m7_result.get("suppliers_business_plans", [])
        swot = {}
        if suppliers_bp:
            best = max(suppliers_bp, key=lambda x: x.get("financials", {}).get("roi", 0))
            swot = best.get("swot", {})

        logger.info(f"[Module 7] ✅ PDF: {m7_result.get('business_plan_pdf')}")
        return {
            **state,
            "business_plan_pdf":       m7_result.get("business_plan_pdf", ""),
            "business_plan_excel":     m7_result.get("business_plan_excel", ""),
            "suppliers_business_plans": suppliers_bp,
            "finance":                 m7_result.get("finance", {}),
            "swot":                    swot,
            "module7_status":          "success",
            "module7_error":           None,
            "completed_modules":       completed + ["module7"],
            "pipeline_errors":         errors,
        }
    except Exception as exc:
        msg = f"Module 7 : exception → {exc}"
        logger.exception(msg)
        return {**state, "module7_status": "error", "module7_error": msg,
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Module 9 — Catalogue multi-format ────────────────────────────────────────

def node_module9_catalogue(state: IndustrieIAState) -> IndustrieIAState:
    logger.info("[Module 9] ▶ Génération Catalogue multi-format")
    completed = list(state.get("completed_modules", []))
    errors    = list(state.get("pipeline_errors", []))
    try:
        sys.path.insert(0, str(ROOT / "modules"))
        from module_9_catalogue import run_module_9  # type: ignore

        # run_module_9 attend : specs, suppliers, all_tco, finance, swot
        suppliers = state.get("suppliers") or _resolve_suppliers(state)
        m9_input = {
            **state,
            "suppliers": suppliers,
        }

        m9_result = run_module_9(m9_input)

        catalogue_files = m9_result.get("catalogue_files", [])
        logger.info(f"[Module 9] ✅ {len(catalogue_files)} fichiers générés")
        for f in catalogue_files:
            logger.info(f"  → {f}")
        return {
            **state,
            "catalogue_files":   catalogue_files,
            "module9_status":    "success",
            "module9_error":     None,
            "completed_modules": completed + ["module9"],
            "pipeline_errors":   errors,
        }
    except Exception as exc:
        msg = f"Module 9 : exception → {exc}"
        logger.exception(msg)
        return {**state, "module9_status": "error", "module9_error": msg,
                "pipeline_errors": errors + [msg], "completed_modules": completed}


# ── Routeurs ──────────────────────────────────────────────────────────────────

def route_after_module1(state: IndustrieIAState) -> str:
    return "module2" if state.get("module1_status") == "success" else "end"

def route_after_module2(state: IndustrieIAState) -> str:
    return "module4" if state.get("module2_status") in ("success", "partial") else "end"

def route_after_module5(state: IndustrieIAState) -> str:
    """Passe à M6 si M5 a produit des offres OU si M4 a des fournisseurs."""
    has_offers   = bool(state.get("final_offers"))
    has_sourcing = bool(state.get("sourcing_results", {}).get("suppliers"))
    return "module6" if (has_offers or has_sourcing) else "end"

def route_after_module6(state: IndustrieIAState) -> str:
    return "module7" if state.get("module6_status") == "success" else "end"

def route_after_module7(state: IndustrieIAState) -> str:
    return "module9" if state.get("module7_status") == "success" else "end"


# ── Construction du graphe ────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(IndustrieIAState)

    # Enregistrer tous les nœuds
    graph.add_node("module1",                node_module1_extract)
    graph.add_node("module2",                node_module2_cad)
    graph.add_node("module4",                node_module4_sourcing)
    graph.add_node("module5_negotiate",      node_module5_negotiate)
    graph.add_node("module5_listen",         node_module5_listen)
    graph.add_node("module5_parse",          node_module5_parse)
    graph.add_node("module6",                node_module6_tco)
    graph.add_node("module7",                node_module7_business_plan)
    graph.add_node("module9",                node_module9_catalogue)

    # Point d'entrée
    graph.set_entry_point("module1")

    # Arêtes conditionnelles
    graph.add_conditional_edges("module1", route_after_module1,
                                 {"module2": "module2", "end": END})
    graph.add_conditional_edges("module2", route_after_module2,
                                 {"module4": "module4", "end": END})
    graph.add_conditional_edges("module5_parse", route_after_module5,
                                 {"module6": "module6", "end": END})
    graph.add_conditional_edges("module6", route_after_module6,
                                 {"module7": "module7", "end": END})
    graph.add_conditional_edges("module7", route_after_module7,
                                 {"module9": "module9", "end": END})

    # Arêtes directes (M4 → M5 chain)
    graph.add_edge("module4",           "module5_negotiate")
    graph.add_edge("module5_negotiate", "module5_listen")
    graph.add_edge("module5_listen",    "module5_parse")

    # Fin
    graph.add_edge("module9", END)

    return graph.compile()


# ── Fonctions publiques pour l'API ────────────────────────────────────────────

def run_pipeline(pdf_path: str) -> IndustrieIAState:
    """Lance le pipeline complet depuis un PDF."""
    app = build_graph()
    return app.invoke({
        "pdf_path": str(pdf_path),
        "pipeline_errors": [],
        "completed_modules": [],
    })


def run_from_module6(specs: dict, suppliers: list,
                     sourcing: dict = None) -> IndustrieIAState:
    """Lance uniquement M6 → M7 → M9 (utile pour tests ou reprise)."""
    state: IndustrieIAState = {
        "specs": specs,
        "suppliers": suppliers,
        "sourcing_results": sourcing or {"suppliers": suppliers, "inflation_rate": 4.5},
        "module1_status": "success",
        "module2_status": "success",
        "module4_status": "success",
        "module5_status": "complete",
        "final_offers": [],
        "pipeline_errors": [],
        "completed_modules": ["module1", "module2", "module4",
                               "module5_negotiate", "module5_listen", "module5_parse"],
    }
    s = node_module6_tco(state)
    s = node_module7_business_plan(s)
    s = node_module9_catalogue(s)
    return s


def run_sourcing_only(specs: dict) -> IndustrieIAState:
    state: IndustrieIAState = {"specs": specs, "module1_status": "success",
                                "pipeline_errors": [], "completed_modules": ["module1", "module2"]}
    return node_module4_sourcing(state)


def run_negotiation_only(specs: dict, sourcing: dict) -> IndustrieIAState:
    state: IndustrieIAState = {"specs": specs, "sourcing_results": sourcing,
                                "module1_status": "success", "module4_status": "success",
                                "pipeline_errors": [], "completed_modules": ["module1", "module2", "module4"]}
    return node_module5_negotiate(state)


def run_parse_only() -> IndustrieIAState:
    state: IndustrieIAState = {"pipeline_errors": [], "completed_modules": []}
    s = node_module5_listen(state)
    return node_module5_parse(s)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="INDUSTRIE IA Pipeline")
    parser.add_argument("--pdf", required=True, help="Chemin vers le PDF technique")
    parser.add_argument("--output", default=None, help="Fichier JSON de sortie")
    args = parser.parse_args()

    result = run_pipeline(args.pdf)

    print(f"\n{'='*60}")
    print(f"Modules complétés : {result.get('completed_modules')}")
    print(f"Erreurs           : {result.get('pipeline_errors')}")

    # M5 — Offres
    offers = result.get("final_offers", [])
    if offers:
        print(f"\n✅ {len(offers)} offres finales :")
        for o in offers:
            print(f"   {o.get('supplier', '?'):30s} → {o.get('unit_price', 0):,} DZD")

    # M6 — TCO
    tco = result.get("tco", {})
    if tco:
        print(f"\n✅ TCO total (1er fournisseur) : {tco.get('total_tco', 0):,.0f} DZD")
        print(f"   Excel : {result.get('tco_excel_path')}")

    # M7 — Business Plan
    if result.get("business_plan_pdf"):
        print(f"\n✅ Business Plan PDF : {result.get('business_plan_pdf')}")
        fin = result.get("finance", {})
        if fin:
            print(f"   ROI : {fin.get('roi_pct')} % | VAN : {fin.get('van_dzd'):,.0f} DZD | TRI : {fin.get('tri_pct')} %")

    # M9 — Catalogue
    catalogue = result.get("catalogue_files", [])
    if catalogue:
        print(f"\n✅ Catalogue ({len(catalogue)} formats) :")
        for f in catalogue:
            print(f"   → {f}")

    if args.output:
        Path(args.output).write_text(
            json.dumps({k: v for k, v in result.items() if k != "extracted_text"},
                       indent=2, ensure_ascii=False))
        print(f"\n💾 Résultat complet → {args.output}")