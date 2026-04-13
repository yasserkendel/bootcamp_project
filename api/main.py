"""
api/main.py

FastAPI backend — INDUSTRIE IA
Interface upload PDF → extraction specs Module 1

Lancer :
    uvicorn api.main:app --reload --port 8000

Puis ouvrir : http://localhost:8000
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Ajout du répertoire racine au sys.path ─────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = FastAPI(
    title="INDUSTRIE IA",
    description="Pipeline IA pour l'industrie mécanique",
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════════════════════
# Route principale — Interface HTML
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index():
    """Sert la page HTML principale."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# Route API — Upload PDF + Extraction Module 1
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/extract")
async def extract_specs(file: UploadFile = File(...)):
    """
    Reçoit un PDF, lance Module 1, retourne les specs en JSON.

    Returns:
        {
            "status": "success" | "error",
            "filename": "vanne_DN100.pdf",
            "specs": { ... },
            "error": null | "message"
        }
    """
    # ── Validation du fichier ──────────────────────────────────────────────────
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Seuls les fichiers PDF sont acceptés."
        )

    # ── Sauvegarde temporaire ──────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        from modules.module1.extractor import extract_text_from_pdf, extract_specs_from_text

        # Extraction texte
        text = extract_text_from_pdf(str(tmp_path))

        if not text.strip():
            return JSONResponse({
                "status": "error",
                "filename": file.filename,
                "specs": {},
                "error": "Aucun texte extractible dans ce PDF. Vérifiez qu'il n'est pas scanné."
            })

        # Analyse LLM
        specs = extract_specs_from_text(text)

        if "error" in specs:
            return JSONResponse({
                "status": "error",
                "filename": file.filename,
                "specs": specs,
                "error": f"Le LLM n'a pas pu analyser le texte : {specs['error']}"
            })

        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "specs": specs,
            "error": None
        })

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "filename": file.filename,
                "specs": {},
                "error": f"Erreur serveur : {str(exc)}"
            }
        )

    finally:
        tmp_path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Route health check
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "INDUSTRIE IA"}