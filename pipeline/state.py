"""pipeline/state.py — État partagé LangGraph INDUSTRIE IA"""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict


class IndustrieIAState(TypedDict, total=False):

    # ── Entrée ────────────────────────────────────────────────────────────────
    pdf_path: str

    # ── Module 1 — Extraction ─────────────────────────────────────────────────
    extracted_text: str
    specs: dict[str, Any]
    module1_status: str
    module1_error: Optional[str]

    # ── Module 2 — CAD ────────────────────────────────────────────────────────
    cad_outputs: dict[str, str]          # {"dxf": "...", "ifc": "..."}
    cad_errors: list[str]
    module2_status: str

    # ── Module 4 — Sourcing ───────────────────────────────────────────────────
    sourcing_results: dict[str, Any]     # {"suppliers": [...], "inflation_rate": 4.5}
    module4_status: str

    # ── Module 5 — Négociation ────────────────────────────────────────────────
    negotiation_output: dict[str, Any]   # {"contacted": [...], "status": "emails_sent"}
    supplier_responses: list[dict]       # emails reçus des fournisseurs
    final_offers: list[dict]             # [{"supplier": ..., "unit_price": ..., "email": ...}]
    module5_status: str
    module5_listen_status: str

    # ── Module 6 — TCO ────────────────────────────────────────────────────────
    suppliers: list[dict]                # liste normalisée transmise à M6/M7/M9
    tco: dict[str, Any]                  # TCO du premier fournisseur (breakdown inclus)
    all_tco: list[dict]                  # TCO complet par fournisseur
    tco_excel_path: str
    tco_json_path: str
    inflation_moyenne: float
    module6_status: str
    module6_error: Optional[str]

    # ── Module 7 — Business Plan ──────────────────────────────────────────────
    business_plan_pdf: str
    business_plan_excel: str
    suppliers_business_plans: list[dict] # données enrichies par fournisseur
    finance: dict[str, Any]              # KPIs financiers (roi, van, tri, tco_total…)
    swot: dict[str, Any]                 # SWOT du meilleur fournisseur
    module7_status: str
    module7_error: Optional[str]

    # ── Module 9 — Catalogue ──────────────────────────────────────────────────
    catalogue_files: list[str]           # [pdf, html, xlsx, json, xml]
    module9_status: str
    module9_error: Optional[str]

    # ── Modules non connectés ─────────────────────────────────────────────────
    video_output: Optional[str]          # Module 3
    digital_twin_output: Optional[dict]  # Module 8

    # ── Métadonnées pipeline ──────────────────────────────────────────────────
    pipeline_errors: list[str]
    completed_modules: list[str]