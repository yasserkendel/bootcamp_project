"""
module3/renderer/manim_renderer.py

Renders a technical animated presentation of the valve using Manim.

The animation covers 5 scenes:
  Scene 1 — Title card  (part name, reference, standard)
  Scene 2 — 2D cross-section build-up with dimension callouts
  Scene 3 — Exploded view of components (body, flanges, stem)
  Scene 4 — Spec table  (PN, DN, material, temperature range)
  Scene 5 — Outro  (OpenIndustry Algérie branding)

Requires:
  pip install manim
  Also needs LaTeX for math text (optional — falls back to plain text)
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# Manim scene source — injected at render time
# ─────────────────────────────────────────────────

MANIM_SCENE_TEMPLATE = '''
from manim import *
import math

# ── Colour palette (industrial) ──────────────────
C_STEEL      = "#B0B8C1"
C_ACCENT     = "#E63946"
C_BG         = "#0D1117"
C_TEXT       = "#F0F6FC"
C_DIM        = "#58A6FF"
C_HATCH      = "#30363D"
C_HIGHLIGHT  = "#FFA657"

config.background_color = C_BG


class ValvePresentation(Scene):
    """Full presentation — all scenes concatenated."""

    def construct(self):
        self.scene_title()
        self.scene_cross_section()
        self.scene_exploded()
        self.scene_spec_table()
        self.scene_outro()

    # ── Scene 1: Title ───────────────────────────

    def scene_title(self):
        title = Text("{part_name}", font_size=42, color=C_TEXT, weight=BOLD)
        ref   = Text("{part_reference}", font_size=28, color=C_ACCENT)
        std   = Text("Norme : {standard}", font_size=22, color=C_STEEL)
        badge = Text("INDUSTRIE IA — OpenIndustry Algérie",
                     font_size=18, color=C_HIGHLIGHT)

        title.move_to(UP * 1.5)
        ref.next_to(title, DOWN, buff=0.4)
        std.next_to(ref, DOWN, buff=0.3)
        badge.to_edge(DOWN, buff=0.5)

        rule = Line(LEFT * 4, RIGHT * 4, color=C_ACCENT, stroke_width=2)
        rule.next_to(std, DOWN, buff=0.3)

        self.play(Write(title), run_time=1.2)
        self.play(FadeIn(ref, shift=UP*0.2), run_time=0.8)
        self.play(FadeIn(std), GrowFromCenter(rule), run_time=0.8)
        self.play(FadeIn(badge), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(VGroup(title, ref, std, rule, badge)))

    # ── Scene 2: 2D cross-section ────────────────

    def scene_cross_section(self):
        scale = 0.012   # mm → Manim units

        f2f        = {f2f} * scale
        body_h     = {body_h} * scale
        flange_od  = {flange_od} * scale
        flange_t   = {flange_t} * scale
        bore       = {bore} * scale
        stem_d     = {stem_d} * scale

        center = ORIGIN

        # Body outline
        body = Rectangle(
            width=f2f, height=body_h * 0.7,
            color=C_STEEL, stroke_width=2
        ).set_fill(C_HATCH, opacity=0.4).move_to(center)

        # Left flange
        lf = Rectangle(
            width=flange_t, height=flange_od,
            color=C_STEEL, stroke_width=2
        ).set_fill(C_HATCH, opacity=0.7)
        lf.move_to(center + LEFT * (f2f/2 - flange_t/2))

        # Right flange
        rf = lf.copy().move_to(center + RIGHT * (f2f/2 - flange_t/2))

        # Bore lines (dashed)
        bore_top = DashedLine(
            center + LEFT*(f2f/2) + UP*(bore/2),
            center + RIGHT*(f2f/2) + UP*(bore/2),
            color=C_DIM, stroke_width=1.5
        )
        bore_bot = bore_top.copy().shift(DOWN * bore)

        # Stem
        stem = Rectangle(
            width=stem_d, height=body_h*0.25,
            color=C_STEEL, stroke_width=2
        ).set_fill(C_STEEL, opacity=0.6)
        stem.next_to(body, UP, buff=0)

        # Centre lines
        h_center = DashedLine(
            center + LEFT*(f2f/2 + 0.2),
            center + RIGHT*(f2f/2 + 0.2),
            color=C_ACCENT, stroke_width=1, dash_length=0.05
        )
        v_center = DashedLine(
            center + DOWN*(body_h*0.4),
            center + UP*(body_h*0.5),
            color=C_ACCENT, stroke_width=1, dash_length=0.05
        )

        heading = Text("COUPE LONGITUDINALE", font_size=22,
                       color=C_ACCENT, weight=BOLD).to_edge(UP)

        # Dimension annotations
        dim_f2f = self._dim_arrow(
            center + LEFT*(f2f/2), center + RIGHT*(f2f/2),
            DOWN * (flange_od/2 + 0.25),
            f"Face à face : {f2f_mm} mm", C_DIM
        )
        dim_dn = self._dim_arrow(
            center + LEFT*(f2f/2 + 0.3) + DOWN*(bore/2),
            center + LEFT*(f2f/2 + 0.3) + UP*(bore/2),
            LEFT * 0.4,
            f"DN {dn} mm", C_DIM, vertical=True
        )

        # Build up the view
        self.play(Write(heading))
        self.play(Create(body), run_time=0.8)
        self.play(Create(lf), Create(rf), run_time=0.6)
        self.play(Create(bore_top), Create(bore_bot), run_time=0.5)
        self.play(Create(stem), run_time=0.4)
        self.play(Create(h_center), Create(v_center), run_time=0.4)
        self.play(FadeIn(dim_f2f), FadeIn(dim_dn), run_time=0.6)
        self.wait(2)
        self.play(FadeOut(VGroup(
            heading, body, lf, rf, bore_top, bore_bot,
            stem, h_center, v_center, dim_f2f, dim_dn
        )))

    def _dim_arrow(self, start, end, offset, label, color,
                   vertical=False):
        mid = (start + end) / 2 + offset
        arrow = DoubleArrow(start + offset, end + offset,
                            color=color, stroke_width=1.5,
                            tip_length=0.1, buff=0)
        txt = Text(label, font_size=14, color=color)
        if vertical:
            txt.rotate(PI/2).next_to(arrow, LEFT, buff=0.1)
        else:
            txt.next_to(arrow, DOWN, buff=0.1)
        return VGroup(arrow, txt)

    # ── Scene 3: Exploded view ───────────────────

    def scene_exploded(self):
        scale = 0.010

        f2f       = {f2f} * scale
        flange_od = {flange_od} * scale
        flange_t  = {flange_t} * scale
        body_h    = {body_h} * scale * 0.7

        heading = Text("VUE ÉCLATÉE — COMPOSANTS",
                       font_size=22, color=C_ACCENT, weight=BOLD).to_edge(UP)
        self.play(Write(heading))

        # Create components at final positions, then animate explosion
        body = Rectangle(width=f2f*0.7, height=body_h,
                         color=C_STEEL).set_fill(C_HATCH, opacity=0.5)
        lf   = Rectangle(width=flange_t, height=flange_od,
                         color=C_STEEL).set_fill(C_STEEL, opacity=0.7)
        rf   = lf.copy()
        stem = Rectangle(width=0.12, height=body_h*0.5,
                         color=C_STEEL).set_fill(C_STEEL, opacity=0.7)

        # Labels
        lbl_body  = Text("Corps", font_size=16, color=C_HIGHLIGHT)
        lbl_lf    = Text("Bride G", font_size=14, color=C_HIGHLIGHT)
        lbl_rf    = Text("Bride D", font_size=14, color=C_HIGHLIGHT)
        lbl_stem  = Text("Tige", font_size=14, color=C_HIGHLIGHT)
        lbl_mat   = Text(f"Matériau : {material}", font_size=16,
                         color=C_TEXT).to_edge(DOWN, buff=0.8)

        # Start assembled
        for obj in [body, lf, rf, stem]:
            obj.move_to(ORIGIN)
        self.play(FadeIn(body), FadeIn(lf), FadeIn(rf), FadeIn(stem))
        self.wait(0.3)

        # Explode
        body_target  = ORIGIN
        lf_target    = LEFT  * (f2f/2 + flange_t + 0.3)
        rf_target    = RIGHT * (f2f/2 + flange_t + 0.3)
        stem_target  = UP    * (body_h/2 + 0.35)

        lbl_body.next_to(body_target,  DOWN, buff=0.15)
        lbl_lf.next_to(lf_target,   DOWN, buff=0.15)
        lbl_rf.next_to(rf_target,   DOWN, buff=0.15)
        lbl_stem.next_to(stem_target, RIGHT, buff=0.1)

        self.play(
            body.animate.move_to(body_target),
            lf.animate.move_to(lf_target),
            rf.animate.move_to(rf_target),
            stem.animate.move_to(stem_target),
            run_time=1.2
        )
        self.play(
            FadeIn(lbl_body), FadeIn(lbl_lf),
            FadeIn(lbl_rf),   FadeIn(lbl_stem),
            FadeIn(lbl_mat),
            run_time=0.6
        )
        self.wait(2)
        self.play(FadeOut(VGroup(
            heading, body, lf, rf, stem,
            lbl_body, lbl_lf, lbl_rf, lbl_stem, lbl_mat
        )))

    # ── Scene 4: Spec table ──────────────────────

    def scene_spec_table(self):
        heading = Text("CARACTÉRISTIQUES TECHNIQUES",
                       font_size=22, color=C_ACCENT, weight=BOLD).to_edge(UP)

        rows = [
            ("Désignation",      "{part_name}"),
            ("Référence",        "{part_reference}"),
            ("Norme",            "{standard}"),
            ("DN",               "{dn} mm"),
            ("PN",               "{pn} bar"),
            ("Pression d'essai", "{pt} bar"),
            ("Température",      "{tmin}°C / +{tmax}°C"),
            ("Matériau corps",   "{material}"),
            ("Siège",            "{seat}"),
            ("Face à face",      "{f2f_mm} mm"),
            ("Quantité",         "{qty} unités"),
        ]

        table_group = VGroup()
        for i, (key, val) in enumerate(rows):
            row_bg = Rectangle(
                width=7, height=0.38,
                fill_color=("#161B22" if i % 2 == 0 else "#0D1117"),
                fill_opacity=1,
                stroke_width=0.5,
                stroke_color=C_HATCH,
            ).move_to(DOWN * (i * 0.4 - 1.8))

            key_txt = Text(key, font_size=15, color=C_DIM,
                           weight=BOLD).move_to(row_bg.get_left() + RIGHT*1.6)
            val_txt = Text(val, font_size=15,
                           color=C_TEXT).move_to(row_bg.get_left() + RIGHT*5.0)
            table_group.add(row_bg, key_txt, val_txt)

        self.play(Write(heading))
        self.play(
            LaggedStart(
                *[FadeIn(m, shift=RIGHT*0.1) for m in table_group],
                lag_ratio=0.05
            ),
            run_time=2
        )
        self.wait(2.5)
        self.play(FadeOut(VGroup(heading, table_group)))

    # ── Scene 5: Outro ───────────────────────────

    def scene_outro(self):
        logo_txt = Text("INDUSTRIE IA", font_size=52,
                        color=C_ACCENT, weight=BOLD)
        sub      = Text("OpenIndustry Algérie", font_size=26, color=C_TEXT)
        tag      = Text("Pipeline open source · LangGraph · Python",
                        font_size=18, color=C_STEEL)
        rule     = Line(LEFT*3, RIGHT*3, color=C_ACCENT, stroke_width=2)

        logo_txt.move_to(UP * 0.8)
        rule.next_to(logo_txt, DOWN, buff=0.3)
        sub.next_to(rule, DOWN, buff=0.3)
        tag.next_to(sub, DOWN, buff=0.3)

        self.play(Write(logo_txt), run_time=1)
        self.play(GrowFromCenter(rule))
        self.play(FadeIn(sub, shift=UP*0.2))
        self.play(FadeIn(tag))
        self.wait(2)
        self.play(FadeOut(VGroup(logo_txt, rule, sub, tag)))
'''


class ManimRenderer:
    """
    Renders the valve presentation using Manim CE.
    """

    WIDTH  = 1920
    HEIGHT = 1080
    FPS    = 24

    def __init__(self, specs: dict[str, Any], output_dir: Path):
        self.specs      = specs
        self.output_dir = output_dir
        self.dims       = specs["dimensions"]
        self.part       = specs["part"]
        self.mech       = specs["mechanical"]
        self.mats       = specs["materials"]

    def is_available(self) -> bool:
        try:
            import manim  # noqa: F401
            return True
        except ImportError:
            return False

    def render(self) -> Path:
        """Write the scene file, run manim CLI, return output path."""
        scene_source = self._build_scene_source()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            scene_file = tmp_path / "valve_scene.py"
            
            with open(scene_file, "w", encoding="utf-8") as f:
                f.write(scene_source)

            output_path = self.output_dir / f"{self.part['reference']}_manim.mp4"

            cmd = [
                sys.executable, "-m", "manim", "render",
                str(scene_file),
                "ValvePresentation",
                "--format", "mp4",
                "-r", "1920,1080",
                "--fps", str(self.FPS),
                "--output_file", str(output_path.resolve()),
                "--media_dir", str((tmp_path / "media").resolve()),
                "-q", "h",
            ]
            
            logger.info("[Manim] Running: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Manim exited {result.returncode}.\n{result.stderr[-1000:]}")

            if not output_path.exists():
                found = list(tmp_path.rglob("*.mp4"))
                if found:
                    import shutil
                    shutil.copy2(found[0], output_path)
                else:
                    raise RuntimeError("Manim completed but output MP4 not found.")

        return output_path


    def _build_scene_source(self) -> str:
        d = self.dims
        m = self.mech
        p = self.part
        return MANIM_SCENE_TEMPLATE.format(
            part_name      = p["name"],
            part_reference = p["reference"],
            standard       = p["standard"],
            f2f            = d["face_to_face_mm"],
            f2f_mm         = d["face_to_face_mm"],
            body_h         = d["body_height_mm"],
            flange_od      = d["flange_od_mm"],
            flange_t       = d["flange_thickness_mm"],
            bore           = d["bore_diameter_mm"],
            stem_d         = d["stem_diameter_mm"],
            dn             = d["nominal_diameter_mm"],
            pn             = m["nominal_pressure_bar"],
            pt             = m["test_pressure_bar"],
            tmin           = m["min_temperature_c"],
            tmax           = m["max_temperature_c"],
            material       = self.mats["body"],
            seat           = self.mats["seat"],
            qty            = p["quantity_required"],
        )
