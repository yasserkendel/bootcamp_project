"""
module2/generators/dxf_generator.py

Generates a technical 2D DXF drawing for an industrial valve
from the structured specs JSON produced by Module 1.

Views generated:
  - Front view (face-to-face cross-section)
  - Top view (flange bolt pattern)
  - Title block with part info and material table
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
from ezdxf.layouts import Modelspace


class DXFGenerator:
    """
    Generates a fully annotated 2D DXF technical drawing
    from valve specification data.
    """

    # Drawing constants
    SCALE = 1.0          # 1:1 in model space
    LINE_WEIGHT = 0.35   # mm
    THIN_LINE = 0.18
    CENTER_LINE_PATTERN = [5.0, -1.5, 0.5, -1.5]

    def __init__(self, specs: dict[str, Any], output_dir: Path):
        self.specs = specs
        self.output_dir = output_dir
        self.dims = specs["dimensions"]
        self.part = specs["part"]
        self.mech = specs["mechanical"]
        self.mats = specs["materials"]
        self.tols = specs["tolerances"]

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def generate(self) -> Path:
        """Generate the DXF and return the output file path."""
        doc = ezdxf.new("R2010", setup=True)
        doc.header["$INSUNITS"] = 4  # millimetres

        self._setup_layers(doc)
        self._setup_linetypes(doc)
        self._setup_text_styles(doc)
        self._setup_dim_styles(doc)

        msp = doc.modelspace()

        # ── Viewport 1: Front view (body cross-section) ──
        self._draw_front_view(msp, origin=(0, 0))

        # ── Viewport 2: Top view (flange bolt pattern) ──
        top_view_origin = (self.dims["face_to_face_mm"] * 1.5 + 60, 0)
        self._draw_top_view(msp, origin=top_view_origin)

        # ── Title block ──────────────────────────────────
        self._draw_title_block(msp)

        # ── Notes & tolerances ────────────────────────────
        self._draw_notes(msp, origin=(0, -self.dims["body_height_mm"] - 80))

        output_path = self.output_dir / f"{self.part['reference']}_drawing.dxf"
        doc.saveas(output_path)
        return output_path

    # ──────────────────────────────────────────
    # Layer / style setup
    # ──────────────────────────────────────────

    def _setup_layers(self, doc: ezdxf.Drawing):
        layers = {
            "VISIBLE":      {"color": colors.WHITE,   "lineweight": 35},
            "HIDDEN":       {"color": colors.BLUE,    "lineweight": 18, "linetype": "DASHED"},
            "CENTER":       {"color": colors.RED,     "lineweight": 18, "linetype": "CENTER"},
            "DIMENSION":    {"color": colors.CYAN,    "lineweight": 18},
            "HATCH":        {"color": colors.YELLOW,  "lineweight": 9},
            "TEXT":         {"color": colors.WHITE,   "lineweight": 18},
            "TITLE_BLOCK":  {"color": colors.WHITE,   "lineweight": 50},
            "NOTES":        {"color": 8,              "lineweight": 13},
        }
        for name, props in layers.items():
            layer = doc.layers.new(name)
            layer.color = props["color"]
            layer.lineweight = props["lineweight"]
            if "linetype" in props:
                layer.linetype = props["linetype"]

    def _setup_linetypes(self, doc: ezdxf.Drawing):
        if "CENTER" not in doc.linetypes:
            doc.linetypes.new("CENTER", dxfattribs={
                "description": "Center line",
                "pattern": [5.0, -1.5, 0.5, -1.5],
            })

    def _setup_text_styles(self, doc: ezdxf.Drawing):
        if "ISO" not in doc.styles:
            doc.styles.new("ISO", dxfattribs={"font": "isocp.shx"})
        if "TITLE" not in doc.styles:
            doc.styles.new("TITLE", dxfattribs={"font": "isocp.shx"})

    def _setup_dim_styles(self, doc: ezdxf.Drawing):
        dimstyle = doc.dimstyles.new("METRIC_ISO")
        dimstyle.dxf.dimtxt = 3.5   # text height
        dimstyle.dxf.dimasz = 3.0   # arrow size
        dimstyle.dxf.dimexo = 1.5   # extension line offset
        dimstyle.dxf.dimexe = 3.0   # extension line extension
        dimstyle.dxf.dimclrd = 6    # dimension line color (magenta)
        dimstyle.dxf.dimclrt = 6

    # ──────────────────────────────────────────
    # Front view — simplified body cross-section
    # ──────────────────────────────────────────

    def _draw_front_view(self, msp: Modelspace, origin: tuple[float, float]):
        ox, oy = origin
        d = self.dims
        f2f = d["face_to_face_mm"]
        body_h = d["body_height_mm"]
        wall = d["wall_thickness_mm"]
        bore = d["bore_diameter_mm"]
        flange_thick = d["flange_thickness_mm"]
        flange_od = d["flange_od_mm"]
        stem_dia = d["stem_diameter_mm"]

        vis = {"layer": "VISIBLE"}
        hid = {"layer": "HIDDEN"}
        ctr = {"layer": "CENTER"}

        # ── Outer body rectangle ────────────────
        half_h = body_h / 2
        msp.add_lwpolyline(
            [(ox, oy - half_h), (ox + f2f, oy - half_h),
             (ox + f2f, oy + half_h), (ox, oy + half_h), (ox, oy - half_h)],
            dxfattribs=vis
        )

        # ── Left flange ──────────────────────────
        half_flange = flange_od / 2
        msp.add_lwpolyline(
            [(ox, oy - half_flange),
             (ox + flange_thick, oy - half_flange),
             (ox + flange_thick, oy + half_flange),
             (ox, oy + half_flange),
             (ox, oy - half_flange)],
            dxfattribs=vis
        )

        # ── Right flange ─────────────────────────
        msp.add_lwpolyline(
            [(ox + f2f, oy - half_flange),
             (ox + f2f - flange_thick, oy - half_flange),
             (ox + f2f - flange_thick, oy + half_flange),
             (ox + f2f, oy + half_flange),
             (ox + f2f, oy - half_flange)],
            dxfattribs=vis
        )

        # ── Bore (hidden lines) ──────────────────
        half_bore = bore / 2
        msp.add_line(
            (ox, oy + half_bore), (ox + f2f, oy + half_bore),
            dxfattribs=hid
        )
        msp.add_line(
            (ox, oy - half_bore), (ox + f2f, oy - half_bore),
            dxfattribs=hid
        )

        # ── Stem ─────────────────────────────────
        half_stem = stem_dia / 2
        stem_base_y = oy + half_h
        stem_top_y = oy + half_h + 60
        msp.add_lwpolyline(
            [(ox + f2f / 2 - half_stem, stem_base_y),
             (ox + f2f / 2 - half_stem, stem_top_y),
             (ox + f2f / 2 + half_stem, stem_top_y),
             (ox + f2f / 2 + half_stem, stem_base_y)],
            dxfattribs=vis
        )

        # ── Center lines ─────────────────────────
        # Horizontal center
        msp.add_line(
            (ox - 15, oy), (ox + f2f + 15, oy),
            dxfattribs=ctr
        )
        # Vertical stem center
        msp.add_line(
            (ox + f2f / 2, oy - half_h - 15),
            (ox + f2f / 2, stem_top_y + 15),
            dxfattribs=ctr
        )

        # ── Cross-hatch on flange sections ───────
        self._add_hatch_rect(msp,
            ox, oy - half_flange,
            flange_thick, flange_od
        )
        self._add_hatch_rect(msp,
            ox + f2f - flange_thick, oy - half_flange,
            flange_thick, flange_od
        )

        # ── Dimensions ───────────────────────────
        dim_y_below = oy - half_flange - 25
        dim_y_above = oy + half_h + 80

        # Face-to-face
        msp.add_linear_dim(
            base=(ox, dim_y_below),
            p1=(ox, oy),
            p2=(ox + f2f, oy),
            dimstyle="METRIC_ISO",
            override={"dimtad": 1}
        ).render()

        # Body height
        msp.add_linear_dim(
            base=(ox + f2f + 30, oy),
            p1=(ox + f2f / 2, oy - half_h),
            p2=(ox + f2f / 2, oy + half_h),
            angle=90,
            dimstyle="METRIC_ISO"
        ).render()

        # Bore diameter label
        msp.add_text(
            f"Ø{bore} (H7)",
            dxfattribs={
                "layer": "TEXT",
                "height": 3.5,
                "insert": (ox + f2f / 2, oy + half_bore + 5),
            }
        )

        # View label
        msp.add_text(
            "VUE DE FACE — COUPE LONGITUDINALE  (1:1)",
            dxfattribs={
                "layer": "TEXT",
                "height": 5,
                "insert": (ox, oy - half_flange - 50),
            }
        )

    # ──────────────────────────────────────────
    # Top view — flange bolt-hole pattern
    # ──────────────────────────────────────────

    def _draw_top_view(self, msp: Modelspace, origin: tuple[float, float]):
        ox, oy = origin
        d = self.dims
        flange_od = d["flange_od_mm"]
        bore = d["bore_diameter_mm"]
        bcd = d["bolt_circle_diameter_mm"]
        n_bolts = d["bolt_holes"]
        bolt_d = d["bolt_hole_diameter_mm"]

        vis = {"layer": "VISIBLE"}
        hid = {"layer": "HIDDEN"}
        ctr = {"layer": "CENTER"}

        # Outer flange circle
        msp.add_circle((ox, oy), flange_od / 2, dxfattribs=vis)

        # Bore circle (hidden)
        msp.add_circle((ox, oy), bore / 2, dxfattribs=hid)

        # Bolt circle (center line)
        msp.add_circle((ox, oy), bcd / 2, dxfattribs=ctr)

        # Bolt holes
        angle_step = 360.0 / n_bolts
        for i in range(n_bolts):
            angle_rad = math.radians(i * angle_step)
            bx = ox + (bcd / 2) * math.cos(angle_rad)
            by = oy + (bcd / 2) * math.sin(angle_rad)
            msp.add_circle((bx, by), bolt_d / 2, dxfattribs=vis)

        # Center lines
        r = flange_od / 2 + 15
        msp.add_line((ox - r, oy), (ox + r, oy), dxfattribs=ctr)
        msp.add_line((ox, oy - r), (ox, oy + r), dxfattribs=ctr)

        # Annotations
        msp.add_text(
            f"Ø{flange_od} (Bride ext.)",
            dxfattribs={"layer": "TEXT", "height": 3.5,
                        "insert": (ox + flange_od / 2 + 5, oy + 5)}
        )
        msp.add_text(
            f"Ø{bcd} (BCD)",
            dxfattribs={"layer": "TEXT", "height": 3.5,
                        "insert": (ox + bcd / 2 + 5, oy - 8)}
        )
        msp.add_text(
            f"{n_bolts}x Ø{bolt_d} trous de boulons",
            dxfattribs={"layer": "TEXT", "height": 3.5,
                        "insert": (ox - flange_od / 2, oy - flange_od / 2 - 20)}
        )

        # View label
        msp.add_text(
            "VUE DE DESSUS — BRIDE  (1:1)",
            dxfattribs={"layer": "TEXT", "height": 5,
                        "insert": (ox - flange_od / 2, oy - flange_od / 2 - 35)}
        )

    # ──────────────────────────────────────────
    # Title block
    # ──────────────────────────────────────────

    def _draw_title_block(self, msp: Modelspace):
        tb_x, tb_y = -20, -350
        w, h = 420, 120
        tb = {"layer": "TITLE_BLOCK"}
        txt = {"layer": "TEXT"}

        # Outer border
        msp.add_lwpolyline([
            (tb_x, tb_y), (tb_x + w, tb_y),
            (tb_x + w, tb_y + h), (tb_x, tb_y + h),
            (tb_x, tb_y)
        ], dxfattribs=tb)

        # Internal dividers
        rows = [25, 50, 75, 100]
        for row in rows:
            msp.add_line(
                (tb_x, tb_y + row), (tb_x + w, tb_y + row),
                dxfattribs=tb
            )
        cols = [140, 280]
        for col in cols:
            msp.add_line(
                (tb_x + col, tb_y), (tb_x + col, tb_y + h),
                dxfattribs=tb
            )

        # Title block content
        p = self.part
        d = self.dims
        m = self.mech
        entries = [
            (tb_x + 5,  tb_y + 105, 5,   p["name"].upper()),
            (tb_x + 5,  tb_y + 80,  3.5, f"Référence : {p['reference']}"),
            (tb_x + 5,  tb_y + 55,  3.5, f"Norme : {p['standard']}"),
            (tb_x + 5,  tb_y + 30,  3.5, f"DN {d['nominal_diameter_mm']} — PN {m['nominal_pressure_bar']}"),
            (tb_x + 5,  tb_y + 8,   3.0, "Projet : INDUSTRIE IA — OpenIndustry Algérie"),

            (tb_x + 145, tb_y + 105, 3.5, "MATÉRIAUX"),
            (tb_x + 145, tb_y + 80,  3.0, f"Corps / Disque : {self.mats['body']}"),
            (tb_x + 145, tb_y + 65,  3.0, f"Tige : {self.mats['stem']}"),
            (tb_x + 145, tb_y + 50,  3.0, f"Siège : {self.mats['seat']}"),
            (tb_x + 145, tb_y + 35,  3.0, f"Joint : {self.mats['gasket']}"),
            (tb_x + 145, tb_y + 20,  3.0, f"Boulonnerie : {self.mats['bolting']}"),

            (tb_x + 285, tb_y + 105, 3.5, "TOLÉRANCES"),
            (tb_x + 285, tb_y + 80,  3.0, f"Alésage : {self.tols['bore_diameter']}"),
            (tb_x + 285, tb_y + 65,  3.0, f"Face à face : {self.tols['face_to_face']}"),
            (tb_x + 285, tb_y + 50,  3.0, f"Planéité bride : {self.tols['flange_flatness']}"),
            (tb_x + 285, tb_y + 30,  3.0, f"Pression d'essai : {m['test_pressure_bar']} bar"),
            (tb_x + 285, tb_y + 8,   3.0, "Echelle : 1:1 — Unités : mm"),
        ]
        for x, y, height, text in entries:
            msp.add_text(text, dxfattribs={
                "layer": "TEXT",
                "height": height,
                "insert": (x, y),
            })

    # ──────────────────────────────────────────
    # Notes section
    # ──────────────────────────────────────────

    def _draw_notes(self, msp: Modelspace, origin: tuple[float, float]):
        ox, oy = origin
        notes = [
            "NOTES GÉNÉRALES :",
            f"1. Toutes les dimensions en millimètres sauf indication contraire.",
            f"2. Matériau : corps et disque en {self.mats['body']} selon EN 10088-3.",
            f"3. Rugosité interne Ra ≤ {self.specs['surface_finish']['internal_roughness_ra']} μm.",
            f"4. Pression nominale PN {self.mech['nominal_pressure_bar']} bar — Pression d'essai {self.mech['test_pressure_bar']} bar.",
            f"5. Température de service : {self.mech['min_temperature_c']}°C à +{self.mech['max_temperature_c']}°C.",
            f"6. Face de bride : {self.specs['surface_finish']['flange_face']} selon EN 1092-1.",
            f"7. Marquage : référence, matériau, PN, DN, température sur le corps.",
            f"8. Quantité requise : {self.part['quantity_required']} unités.",
        ]
        for i, note in enumerate(notes):
            msp.add_text(note, dxfattribs={
                "layer": "NOTES",
                "height": 3.0 if i > 0 else 4.0,
                "insert": (ox, oy - i * 8),
            })

    # ──────────────────────────────────────────
    # Helper: add a cross-hatch to a rectangle
    # ──────────────────────────────────────────

    def _add_hatch_rect(self, msp: Modelspace,
                        x: float, y: float,
                        w: float, h: float,
                        spacing: float = 4.0):
        hatch = msp.add_hatch(color=colors.YELLOW, dxfattribs={"layer": "HATCH"})
        hatch.set_pattern_fill("ANSI31", scale=0.5)
        hatch.paths.add_polyline_path(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
            is_closed=True
        )
