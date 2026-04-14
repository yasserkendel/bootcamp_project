"""
api/main.py — INDUSTRIE IA
Lancer : uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="INDUSTRIE IA", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ══════════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ══════════════════════════════════════════════════════════════════════════════

class CADRequest(BaseModel):
    specs: dict[str, Any]
    formats: dict[str, bool] = {"dxf": True, "ifc": True}

class SourcingRequest(BaseModel):
    specs: dict[str, Any] = {}

class NegotiateRequest(BaseModel):
    specs: dict[str, Any] = {}
    sourcing: dict[str, Any] = {}

class TCORequest(BaseModel):
    """
    Entrée pour M6.
    Si suppliers est vide, M6 utilise ses données mock internes.
    Si final_offers est fourni (depuis M5), il sera prioritaire.
    """
    specs: dict[str, Any] = {}
    suppliers: list[dict[str, Any]] = []
    final_offers: list[dict[str, Any]] = []   # depuis M5
    sourcing_results: dict[str, Any] = {}     # depuis M4
    quantite: int = 200
    years: int = 10

class BusinessPlanRequest(BaseModel):
    """
    Entrée pour M7.
    Accepte les sorties de M6 directement.
    """
    specs: dict[str, Any] = {}
    suppliers: list[dict[str, Any]] = []
    tco: dict[str, Any] = {}
    all_tco: list[dict[str, Any]] = []
    inflation_moyenne: float = 5.2

class CatalogueRequest(BaseModel):
    """
    Entrée pour M9.
    Accepte les sorties de M6 + M7 directement.
    """
    specs: dict[str, Any] = {}
    suppliers: list[dict[str, Any]] = []
    all_tco: list[dict[str, Any]] = []
    finance: dict[str, Any] = {}
    swot: dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════════
# Pages HTML
# ══════════════════════════════════════════════════════════════════════════════

def _html(name: str) -> HTMLResponse:
    path = Path(__file__).parent / "templates" / name
    return HTMLResponse(content=path.read_text(encoding="utf-8"))

@app.get("/",          response_class=HTMLResponse)
async def index():        return _html("index.html")

@app.get("/module2",   response_class=HTMLResponse)
async def module2():      return _html("module2.html")

@app.get("/module4_5", response_class=HTMLResponse)
async def module45():     return _html("module4_5.html")

@app.get("/module6_7_9", response_class=HTMLResponse)
async def module679():
    return _html("module6_7_9.html")
# ══════════════════════════════════════════════════════════════════════════════
# API — Module 1 : Extraction PDF
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/extract")
async def extract_specs(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        from modules.module1.extractor import extract_text_from_pdf, extract_specs_from_text

        text = extract_text_from_pdf(str(tmp_path))
        if not text.strip():
            return JSONResponse({"status": "error", "filename": file.filename,
                                 "specs": {}, "error": "Aucun texte extractible dans ce PDF."})

        specs = extract_specs_from_text(text)
        if "error" in specs:
            return JSONResponse({"status": "error", "filename": file.filename,
                                 "specs": specs, "error": f"LLM error : {specs['error']}"})

        return JSONResponse({"status": "success", "filename": file.filename,
                             "specs": specs, "error": None})

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "filename": file.filename,
                                     "specs": {}, "error": f"Erreur serveur : {exc}"})
    finally:
        tmp_path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 2 : Génération CAD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/generate-cad")
async def generate_cad(request: CADRequest):
    if not request.specs:
        return JSONResponse(status_code=400,
                            content={"status": "error",
                                     "cad_outputs": {"dxf": "", "ifc": ""},
                                     "cad_errors": ["Aucune specs fournie."]})
    try:
        from modules.module2.agent.cad_agent import run_cad_generation

        result      = run_cad_generation({"specs": request.specs,
                                          "cad_outputs": {}, "cad_errors": []})
        cad_outputs = result.get("cad_outputs", {"dxf": "", "ifc": ""})
        cad_errors  = result.get("cad_errors",  [])

        if not request.formats.get("dxf"): cad_outputs["dxf"] = ""
        if not request.formats.get("ifc"): cad_outputs["ifc"] = ""

        sizes = {fmt: f"{Path(p).stat().st_size/1024:.1f} KB"
                 for fmt, p in cad_outputs.items() if p and Path(p).exists()}

        status = ("success" if not cad_errors
                  else "partial" if any(cad_outputs.values())
                  else "error")

        return JSONResponse({"status": status, "cad_outputs": cad_outputs,
                             "cad_errors": cad_errors, "sizes": sizes})

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error",
                                     "cad_outputs": {"dxf": "", "ifc": ""},
                                     "cad_errors": [f"Erreur serveur : {exc}"],
                                     "sizes": {}})


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 4 : Sourcing fournisseurs
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/sourcing")
async def sourcing(request: SourcingRequest):
    try:
        from pipeline.graph import run_sourcing_only
        result = run_sourcing_only(request.specs)
        return JSONResponse({
            "status":   result.get("module4_status", "error"),
            "sourcing": result.get("sourcing_results", {}),
            "errors":   result.get("pipeline_errors", []),
        })
    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 5a : Négociation
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/negotiate")
async def negotiate(request: NegotiateRequest):
    try:
        from pipeline.graph import run_negotiation_only
        result = run_negotiation_only(request.specs, request.sourcing)
        return JSONResponse({
            "status":      result.get("module5_status", "error"),
            "negotiation": result.get("negotiation_output", {}),
            "errors":      result.get("pipeline_errors", []),
        })
    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 5b+c : Lecture réponses + Analyse offres
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/parse-offers")
async def parse_offers():
    try:
        from pipeline.graph import run_parse_only
        result = run_parse_only()
        return JSONResponse({
            "status":          result.get("module5_status", "error"),
            "offers":          result.get("final_offers", []),
            "responses_count": len(result.get("supplier_responses", [])),
            "errors":          result.get("pipeline_errors", []),
        })
    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 6 : TCO
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/tco")
async def compute_tco(request: TCORequest):
    """
    Calcule le TCO pour les fournisseurs fournis.
    Transmet final_offers et sourcing_results au graphe pour que
    _resolve_suppliers() puisse construire la liste correctement.
    """
    try:
        from pipeline.graph import node_module6_tco
        from pipeline.state import IndustrieIAState

        state: IndustrieIAState = {
            "specs":            request.specs,
            "suppliers":        request.suppliers,
            "final_offers":     request.final_offers,
            "sourcing_results": request.sourcing_results,
            "pipeline_errors":  [],
            "completed_modules": [],
        }

        result = node_module6_tco(state)

        return JSONResponse({
            "status":            result.get("module6_status", "error"),
            "tco":               result.get("tco", {}),
            "all_tco":           result.get("all_tco", []),
            "inflation_moyenne": result.get("inflation_moyenne", 0),
            "tco_excel_path":    result.get("tco_excel_path", ""),
            "tco_json_path":     result.get("tco_json_path", ""),
            "errors":            result.get("pipeline_errors", []),
        })

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


@app.get("/api/tco/download")
async def download_tco_excel():
    """Télécharge le fichier Excel TCO généré par M6."""
    path = Path("outputs/tco_report.xlsx")
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail="Fichier TCO non trouvé. Lancez d'abord /api/tco.")
    return FileResponse(path=str(path),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename="tco_report.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 7 : Business Plan
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/business-plan")
async def generate_business_plan(request: BusinessPlanRequest):
    """
    Génère le business plan PDF + Excel.
    Accepte directement les sorties de /api/tco.
    """
    try:
        from pipeline.graph import node_module7_business_plan
        from pipeline.state import IndustrieIAState

        state: IndustrieIAState = {
            "specs":             request.specs,
            "suppliers":         request.suppliers,
            "tco":               request.tco,
            "all_tco":           request.all_tco,
            "inflation_moyenne": request.inflation_moyenne,
            "pipeline_errors":   [],
            "completed_modules": [],
        }

        result = node_module7_business_plan(state)

        return JSONResponse({
            "status":                   result.get("module7_status", "error"),
            "business_plan_pdf":        result.get("business_plan_pdf", ""),
            "business_plan_excel":      result.get("business_plan_excel", ""),
            "finance":                  result.get("finance", {}),
            "swot":                     result.get("swot", {}),
            "suppliers_business_plans": result.get("suppliers_business_plans", []),
            "errors":                   result.get("pipeline_errors", []),
        })

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


@app.get("/api/business-plan/download/pdf")
async def download_bp_pdf():
    """Télécharge le Business Plan PDF."""
    path = Path("outputs/business_plan.pdf")
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail="Business plan non trouvé. Lancez d'abord /api/business-plan.")
    return FileResponse(path=str(path), media_type="application/pdf",
                        filename="business_plan.pdf")


@app.get("/api/business-plan/download/excel")
async def download_bp_excel():
    """Télécharge le Business Plan Excel."""
    path = Path("outputs/business_plan_projections.xlsx")
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail="Business plan Excel non trouvé.")
    return FileResponse(path=str(path),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename="business_plan_projections.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# API — Module 9 : Catalogue multi-format
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/catalogue")
async def generate_catalogue(request: CatalogueRequest):
    """
    Génère le catalogue en 5 formats (PDF, HTML, Excel, JSON, XML).
    Accepte directement les sorties de /api/tco et /api/business-plan.
    """
    try:
        from pipeline.graph import node_module9_catalogue
        from pipeline.state import IndustrieIAState

        state: IndustrieIAState = {
            "specs":             request.specs,
            "suppliers":         request.suppliers,
            "all_tco":           request.all_tco,
            "finance":           request.finance,
            "swot":              request.swot,
            "pipeline_errors":   [],
            "completed_modules": [],
        }

        result = node_module9_catalogue(state)

        return JSONResponse({
            "status":          result.get("module9_status", "error"),
            "catalogue_files": result.get("catalogue_files", []),
            "errors":          result.get("pipeline_errors", []),
        })

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})


@app.get("/api/catalogue/download/{format}")
async def download_catalogue(format: str):
    """
    Télécharge un format du catalogue.
    format : pdf | html | xlsx | json | xml
    """
    allowed = {
        "pdf":  ("outputs/catalogue.pdf",  "application/pdf",                    "catalogue.pdf"),
        "html": ("outputs/catalogue.html", "text/html",                           "catalogue.html"),
        "xlsx": ("outputs/catalogue.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "catalogue.xlsx"),
        "json": ("outputs/catalogue.json", "application/json",                    "catalogue.json"),
        "xml":  ("outputs/catalogue.xml",  "application/xml",                     "catalogue.xml"),
    }
    if format not in allowed:
        raise HTTPException(status_code=400,
                            detail=f"Format invalide. Choisir parmi : {list(allowed.keys())}")
    file_path, media_type, filename = allowed[format]
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404,
                            detail=f"Catalogue .{format} non trouvé. Lancez d'abord /api/catalogue.")
    return FileResponse(path=str(path), media_type=media_type, filename=filename)


# ══════════════════════════════════════════════════════════════════════════════
# API — Pipeline complet (M1 → M9)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/pipeline/full")
async def run_full_pipeline(file: UploadFile = File(...)):
    """
    Lance le pipeline complet depuis un PDF :
    M1 → M2 → M4 → M5 → M6 → M7 → M9
    Retourne un résumé de toutes les sorties.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        from pipeline.graph import run_pipeline

        result = run_pipeline(str(tmp_path))

        # Construire la réponse résumée (on exclut extracted_text — trop lourd)
        return JSONResponse({
            "status":            "success" if not result.get("pipeline_errors") else "partial",
            "completed_modules": result.get("completed_modules", []),
            "errors":            result.get("pipeline_errors", []),

            # M1
            "specs": result.get("specs", {}),

            # M2
            "cad_outputs": result.get("cad_outputs", {}),

            # M4
            "sourcing": result.get("sourcing_results", {}),

            # M5
            "final_offers": result.get("final_offers", []),

            # M6
            "tco":              result.get("tco", {}),
            "tco_excel_path":   result.get("tco_excel_path", ""),
            "inflation_moyenne": result.get("inflation_moyenne", 0),

            # M7
            "business_plan_pdf":   result.get("business_plan_pdf", ""),
            "business_plan_excel": result.get("business_plan_excel", ""),
            "finance":             result.get("finance", {}),

            # M9
            "catalogue_files": result.get("catalogue_files", []),
        })

    except Exception as exc:
        return JSONResponse(status_code=500,
                            content={"status": "error", "error": str(exc)})
    finally:
        tmp_path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Health check
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    modules_ready = []
    for mod in ["module1", "module2", "module4_5", "module_6_tco",
                "module_7_business_plan", "module_9_catalogue"]:
        path = ROOT / "modules" / f"{mod}.py"
        if not path.exists():
            path = ROOT / "modules" / mod
        modules_ready.append({"module": mod, "found": path.exists()})

    return {
        "status":  "ok",
        "service": "INDUSTRIE IA",
        "modules": modules_ready,
    }