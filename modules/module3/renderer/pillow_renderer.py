"""
module3/renderer/pillow_renderer.py

Pure-Python fallback renderer using Pillow + imageio.

Generates a sequence of annotated PNG frames and stitches them
into an MP4. No Blender, no Manim, no LaTeX required.

The video contains 5 sections:
  1. Title card
  2. Animated 2D cross-section build-up
  3. Rotating "orbit" of component labels (exploded view metaphor)
  4. Scrolling spec sheet
  5. Outro branding

Output: 1920×1080 MP4 at 24 fps, ~8 seconds total (~192 frames)

Dependencies:
    pip install pillow imageio imageio-ffmpeg
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────
BG       = (13,  17,  23)       # dark navy
STEEL    = (176, 184, 193)      # stainless steel grey
ACCENT   = (230, 57,  70)       # industrial red
DIM_COL  = (88,  166, 255)      # blueprint blue
TEXT_COL = (240, 246, 252)      # near-white
HATCH    = (48,  54,  61)       # dark grey fill
HIGHLIGHT= (255, 166, 87)       # amber

W, H = 1920, 1080
FPS  = 24


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a decent font; fall back to default."""
    candidates = [
        "arial.ttf", "Arial.ttf",
        "DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _centred_text(draw: ImageDraw.ImageDraw, y: int, text: str,
                  font, color, x_offset: int = 0):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2 + x_offset, y), text, font=font, fill=color)


def _rect(draw: ImageDraw.ImageDraw, x, y, w, h, color, fill=None, width=2):
    draw.rectangle([x, y, x+w, y+h], outline=color, fill=fill, width=width)


class PillowRenderer:
    """Frame-by-frame renderer using only Pillow and imageio."""

    TOTAL_FRAMES = FPS * 9   # 9 seconds

    def __init__(self, specs: dict[str, Any], output_dir: Path):
        self.specs      = specs
        self.output_dir = output_dir
        self.dims       = specs["dimensions"]
        self.part       = specs["part"]
        self.mech       = specs["mechanical"]
        self.mats       = specs["materials"]

    # module3/renderer/pillow_renderer.py

    def render(self) -> Path:
       
        import imageio
        imageio.mimwrite(str(output_path), frames, fps=24)
        return output_path

    # ─────────────────────────────────────────────
    # Frame generation — 5 sections
    # ─────────────────────────────────────────────

    def _generate_all_frames(self) -> list:
        import numpy as np
        all_frames: list = []

        seg = self.TOTAL_FRAMES // 5  # frames per section

        for i in range(seg):          all_frames.append(np.array(self._frame_title(i, seg)))
        for i in range(seg):          all_frames.append(np.array(self._frame_cross_section(i, seg)))
        for i in range(seg):          all_frames.append(np.array(self._frame_exploded(i, seg)))
        for i in range(seg):          all_frames.append(np.array(self._frame_specs(i, seg)))
        for i in range(seg):          all_frames.append(np.array(self._frame_outro(i, seg)))

        return all_frames

    # ── Section 1: Title ─────────────────────────

    def _frame_title(self, t: int, total: int) -> Image.Image:
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        p    = self.part

        alpha = min(1.0, t / (total * 0.3))   # fade-in

        f_big  = _font(72)
        f_med  = _font(42)
        f_sml  = _font(28)
        f_tag  = _font(22)

        # Red accent bar
        bar_w = int(W * 0.6 * alpha)
        draw.rectangle([W//2 - bar_w//2, H//2 - 120,
                        W//2 + bar_w//2, H//2 - 116], fill=ACCENT)

        _centred_text(draw, H//2 - 100, p["name"].upper(), f_big,
                      tuple(int(c*alpha) for c in TEXT_COL))
        _centred_text(draw, H//2 - 10,  p["reference"],    f_med,
                      tuple(int(c*alpha) for c in list(ACCENT)))
        _centred_text(draw, H//2 + 50,  f"Norme : {p['standard']}", f_sml,
                      tuple(int(c*alpha) for c in list(STEEL)))

        # Bottom tag
        _centred_text(draw, H - 80,
                      "INDUSTRIE IA  ·  OpenIndustry Algérie  ·  Pipeline open source",
                      f_tag, HIGHLIGHT)

        # Corner reference box
        draw.rectangle([40, 40, 340, 100], outline=ACCENT, width=1)
        draw.text((50, 50), "MODULE 3 — PRÉSENTATION", font=_font(18), fill=ACCENT)

        return img

    # ── Section 2: 2D Cross-section ──────────────

    def _frame_cross_section(self, t: int, total: int) -> Image.Image:
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        d    = self.dims

        prog = t / total   # 0 → 1

        # Scale mm → pixels  (250mm face-to-face = 500px)
        S    = 2.0
        cx, cy = W // 2, H // 2

        f2f   = int(d["face_to_face_mm"]   * S)
        bh    = int(d["body_height_mm"]    * S * 0.55)
        ft    = int(d["flange_thickness_mm"]* S)
        fod   = int(d["flange_od_mm"]      * S)
        bore  = int(d["bore_diameter_mm"]  * S)
        stem_w= int(d["stem_diameter_mm"]  * S)
        stem_h= int(60 * S)

        # Draw in stages gated by progress
        # Stage 0–0.2: body outline
        if prog > 0.0:
            _rect(draw, cx - f2f//2, cy - bh//2, f2f, bh, STEEL, HATCH, 2)

        # Stage 0.2–0.4: flanges
        if prog > 0.2:
            _rect(draw, cx - f2f//2,            cy - fod//2, ft, fod, STEEL, HATCH, 2)
            _rect(draw, cx + f2f//2 - ft,       cy - fod//2, ft, fod, STEEL, HATCH, 2)

        # Stage 0.4–0.6: bore dashed lines
        if prog > 0.4:
            dash_len = 12
            x = cx - f2f//2
            while x < cx + f2f//2:
                draw.line([(x, cy - bore//2), (min(x+dash_len, cx+f2f//2), cy - bore//2)],
                          fill=DIM_COL, width=1)
                draw.line([(x, cy + bore//2), (min(x+dash_len, cx+f2f//2), cy + bore//2)],
                          fill=DIM_COL, width=1)
                x += dash_len * 2

        # Stage 0.6–0.8: stem
        if prog > 0.6:
            _rect(draw, cx - stem_w//2, cy - bh//2 - stem_h,
                  stem_w, stem_h, STEEL, HATCH, 2)

        # Stage 0.8+: dimensions
        if prog > 0.8:
            # Face-to-face dimension line
            dim_y = cy + fod//2 + 30
            draw.line([(cx - f2f//2, dim_y), (cx + f2f//2, dim_y)],
                      fill=DIM_COL, width=1)
            draw.line([(cx - f2f//2, dim_y-8), (cx - f2f//2, dim_y+8)],
                      fill=DIM_COL, width=1)
            draw.line([(cx + f2f//2, dim_y-8), (cx + f2f//2, dim_y+8)],
                      fill=DIM_COL, width=1)
            draw.text((cx - 80, dim_y + 8),
                      f"Face à face : {d['face_to_face_mm']} mm",
                      font=_font(20), fill=DIM_COL)

            # DN label
            draw.text((cx - f2f//2 - 140, cy - bore//4),
                      f"Ø {d['bore_diameter_mm']} mm",
                      font=_font(20), fill=DIM_COL)

        # Centre lines
        draw.line([(cx - f2f//2 - 20, cy), (cx + f2f//2 + 20, cy)],
                  fill=ACCENT, width=1)
        draw.line([(cx, cy - bh//2 - 20), (cx, cy + bh//2 + 20)],
                  fill=ACCENT, width=1)

        # Title
        draw.text((60, 40), "COUPE LONGITUDINALE  —  VUE DE FACE  (1:1)",
                  font=_font(26), fill=ACCENT)

        return img

    # ── Section 3: Exploded view ──────────────────

    def _frame_exploded(self, t: int, total: int) -> Image.Image:
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        d    = self.dims

        S = 1.5
        cx, cy = W // 2, H // 2

        f2f   = int(d["face_to_face_mm"]   * S * 0.6)
        bh    = int(d["body_height_mm"]    * S * 0.4)
        ft    = int(d["flange_thickness_mm"]* S)
        fod   = int(d["flange_od_mm"]      * S * 0.7)

        # Explode fraction 0→1 over first 60% of section
        explode = min(1.0, t / (total * 0.6))
        gap = int(explode * 80)

        # Body (stays centred)
        bx, by = cx - f2f//2, cy - bh//2
        _rect(draw, bx, by, f2f, bh, STEEL, HATCH, 2)
        draw.text((cx - 30, cy - bh//2 - 30), "Corps", font=_font(22), fill=HIGHLIGHT)

        # Left flange — moves left
        lx = cx - f2f//2 - ft - gap
        _rect(draw, lx, cy - fod//2, ft, fod, STEEL, STEEL, 2)
        draw.text((lx - 10, cy - fod//2 - 30), "Bride G.", font=_font(20), fill=HIGHLIGHT)

        # Right flange — moves right
        rx = cx + f2f//2 + gap
        _rect(draw, rx, cy - fod//2, ft, fod, STEEL, STEEL, 2)
        draw.text((rx, cy - fod//2 - 30), "Bride D.", font=_font(20), fill=HIGHLIGHT)

        # Stem — moves up
        stem_w = int(d["stem_diameter_mm"] * S)
        stem_h = int(60 * S)
        sy = cy - bh//2 - stem_h - gap
        _rect(draw, cx - stem_w//2, sy, stem_w, stem_h, STEEL, STEEL, 2)
        draw.text((cx + stem_w//2 + 10, sy + stem_h//2 - 10),
                  "Tige", font=_font(20), fill=HIGHLIGHT)

        # Material annotation (appears after explode)
        if explode > 0.9:
            draw.text((60, H - 120),
                      f"Matériau :  {self.mats['body']}",
                      font=_font(26), fill=TEXT_COL)
            draw.text((60, H - 80),
                      f"Siège :  {self.mats['seat']}",
                      font=_font(22), fill=STEEL)

        draw.text((60, 40), "VUE ÉCLATÉE — COMPOSANTS PRINCIPAUX",
                  font=_font(26), fill=ACCENT)

        return img

    # ── Section 4: Spec sheet ─────────────────────

    def _frame_specs(self, t: int, total: int) -> Image.Image:
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        d    = self.dims
        m    = self.mech
        p    = self.part

        rows = [
            ("Désignation",       p["name"]),
            ("Référence",         p["reference"]),
            ("Norme",             p["standard"]),
            ("DN (Ø nominal)",    f"{d['nominal_diameter_mm']} mm"),
            ("PN (pression nom.)",f"{m['nominal_pressure_bar']} bar"),
            ("Pression d'essai",  f"{m['test_pressure_bar']} bar"),
            ("Température min",   f"{m['min_temperature_c']} °C"),
            ("Température max",   f"{m['max_temperature_c']} °C"),
            ("Matériau corps",    self.mats["body"]),
            ("Siège",             self.mats["seat"]),
            ("Face à face",       f"{d['face_to_face_mm']} mm"),
            ("Bride OD",          f"{d['flange_od_mm']} mm"),
            ("Nombre de boulons", f"{d['bolt_holes']}x Ø{d['bolt_hole_diameter_mm']} mm"),
            ("Quantité req.",     f"{p['quantity_required']} unités"),
        ]

        draw.text((60, 40), "FICHE TECHNIQUE — CARACTÉRISTIQUES",
                  font=_font(28), fill=ACCENT)
        draw.line([(60, 90), (W-60, 90)], fill=ACCENT, width=2)

        # Scroll effect: reveal rows progressively
        visible = max(1, int((t / total) * len(rows) * 1.3))
        row_h = 52
        start_y = 110
        col1_x, col2_x = 80, 620

        for i, (key, val) in enumerate(rows[:visible]):
            y = start_y + i * row_h
            if y > H - 80:
                break
            bg_col = (22, 27, 34) if i % 2 == 0 else (13, 17, 23)
            draw.rectangle([60, y, W-60, y + row_h - 4], fill=bg_col)
            draw.text((col1_x, y + 12), key, font=_font(22), fill=DIM_COL)
            draw.text((col2_x, y + 12), val, font=_font(22), fill=TEXT_COL)

        # Bottom strip
        draw.rectangle([0, H-60, W, H], fill=(22, 27, 34))
        _centred_text(draw, H-45,
                      "INDUSTRIE IA  ·  Module 2 → DXF + IFC  ·  Module 3 → Vidéo HD",
                      _font(18), STEEL)

        return img

    # ── Section 5: Outro ─────────────────────────

    def _frame_outro(self, t: int, total: int) -> Image.Image:
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        alpha = min(1.0, t / (total * 0.4))

        # Animated concentric rings
        max_r = int(min(W, H) * 0.45)
        rings = 5
        for i in range(rings):
            r = int(max_r * (i + 1) / rings)
            pulse = 0.15 + 0.05 * math.sin(t / total * 2 * math.pi + i)
            col = tuple(int(c * pulse * alpha) for c in ACCENT)
            draw.ellipse(
                [W//2 - r, H//2 - r, W//2 + r, H//2 + r],
                outline=col, width=1
            )

        f_logo = _font(80)
        f_sub  = _font(32)
        f_tag  = _font(22)

        col_logo = tuple(int(c * alpha) for c in ACCENT)
        col_text = tuple(int(c * alpha) for c in TEXT_COL)
        col_steel= tuple(int(c * alpha) for c in STEEL)

        _centred_text(draw, H//2 - 80,  "INDUSTRIE IA",          f_logo, col_logo)
        _centred_text(draw, H//2 + 20,  "OpenIndustry Algérie",  f_sub,  col_text)
        _centred_text(draw, H//2 + 70,  "LangGraph · Python · Open Source", f_tag, col_steel)

        draw.line([(W//2 - 200, H//2 + 10), (W//2 + 200, H//2 + 10)],
                  fill=col_logo, width=2)

        return img
