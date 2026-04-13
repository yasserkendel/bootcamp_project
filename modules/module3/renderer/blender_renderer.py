"""
module3/renderer/blender_renderer.py

Renders a photorealistic 3D animation of the industrial valve
using Blender in headless (--background) mode.

Blender is driven by a generated Python script that:
  - Imports the valve geometry from the IFC file
  - Sets up industrial lighting (3-point + HDRI)
  - Applies a stainless steel material (metallic BSDF)
  - Animates a 360° turntable rotation over 120 frames
  - Renders each frame and assembles them into an MP4

Requires:
  - Blender 3.x or 4.x installed and on PATH (or BLENDER_PATH env var set)
  - blenderbim addon installed in Blender (for IFC import)
    Install: https://blenderbim.org/
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BLENDER_SCRIPT_TEMPLATE = '''
import bpy
import math
import sys
import os

# ── Clear default scene ───────────────────────────────────────────
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

# ── Import IFC via BlenderBIM ─────────────────────────────────────
ifc_path = r"{ifc_path}"
if os.path.exists(ifc_path):
    try:
        bpy.ops.bim.load_project(filepath=ifc_path)
        print("[Module3-Blender] IFC imported successfully")
    except Exception as e:
        print(f"[Module3-Blender] IFC import failed ({{e}}), generating procedural geometry")
        _build_procedural_valve()
else:
    print("[Module3-Blender] IFC file not found, generating procedural geometry")
    _build_procedural_valve()


def _build_procedural_valve():
    """Fallback: build a stylised valve from Blender primitives."""
    # Body cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius={body_radius}, depth={f2f},
        location=(0, 0, 0)
    )
    body = bpy.context.active_object
    body.name = "ValveBody"

    # Left flange disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius={flange_radius}, depth={flange_thick},
        location=(-{flange_offset}, 0, 0)
    )
    bpy.context.active_object.name = "LeftFlange"

    # Right flange disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius={flange_radius}, depth={flange_thick},
        location=({flange_offset}, 0, 0)
    )
    bpy.context.active_object.name = "RightFlange"

    # Stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius={stem_radius}, depth={stem_height},
        location=(0, 0, {stem_z})
    )
    bpy.context.active_object.name = "Stem"


# ── Stainless steel material ──────────────────────────────────────
def apply_steel_material(obj):
    mat = bpy.data.materials.new(name="Inox316L")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value       = (0.72, 0.72, 0.75, 1.0)
    bsdf.inputs["Metallic"].default_value         = 1.0
    bsdf.inputs["Roughness"].default_value        = 0.15
    bsdf.inputs["Specular IOR Level"].default_value = 0.9
    if obj.data:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

for obj in bpy.data.objects:
    if obj.type == "MESH":
        apply_steel_material(obj)

# ── Lighting — 3-point industrial setup ──────────────────────────
# Key light
bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
key = bpy.context.active_object
key.data.energy  = 800
key.data.size    = 2.0
key.rotation_euler = (math.radians(45), 0, math.radians(45))

# Fill light
bpy.ops.object.light_add(type="AREA", location=(-3, 2, 2))
fill = bpy.context.active_object
fill.data.energy = 300
fill.data.size   = 3.0

# Rim light
bpy.ops.object.light_add(type="SPOT", location=(0, 4, 5))
rim = bpy.context.active_object
rim.data.energy     = 500
rim.data.spot_size  = math.radians(30)
rim.rotation_euler  = (math.radians(-45), 0, 0)

# World background — dark studio
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.03, 1)
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ── Camera ───────────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0.5, -1.2, 0.4))
cam = bpy.context.active_object
cam.data.lens = 85
bpy.context.scene.camera = cam

# Point camera at origin
import mathutils
direction = mathutils.Vector((0, 0, 0)) - cam.location
rot_quat  = direction.to_track_quat("-Z", "Y")
cam.rotation_euler = rot_quat.to_euler()

# ── Empty at origin for turntable pivot ──────────────────────────
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
pivot = bpy.context.active_object
pivot.name = "TurntablePivot"

# Parent camera to pivot
cam.parent = pivot

# ── Animation — 360° turntable over {total_frames} frames ────────
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = {total_frames}
scene.render.fps  = {fps}

pivot.rotation_euler = (0, 0, 0)
pivot.keyframe_insert(data_path="rotation_euler", frame=1)
pivot.rotation_euler = (0, 0, math.radians(360))
pivot.keyframe_insert(data_path="rotation_euler", frame={total_frames})

# Make rotation linear (no easing)
for fc in pivot.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"

# ── Title card overlay text ───────────────────────────────────────
# Note: requires font rendering — skip if font not available
try:
    bpy.ops.object.text_add(location=(-0.8, 0, -0.6))
    txt = bpy.context.active_object
    txt.data.body      = "{part_reference}\\n{part_name}"
    txt.data.size      = 0.06
    txt.data.align_x   = "LEFT"
    txt.rotation_euler = (math.radians(90), 0, 0)
    mat_txt = bpy.data.materials.new("TextMat")
    mat_txt.use_nodes = True
    mat_txt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1)
    txt.data.materials.append(mat_txt)
except Exception:
    pass

# ── Render settings ───────────────────────────────────────────────
render = scene.render
render.engine               = "CYCLES"
render.resolution_x         = {width}
render.resolution_y         = {height}
render.resolution_percentage = 100
render.image_settings.file_format = "FFMPEG"
render.ffmpeg.format        = "MPEG4"
render.ffmpeg.codec         = "H264"
render.ffmpeg.constant_rate_factor = "MEDIUM"
render.ffmpeg.audio_codec   = "NONE"
render.filepath             = r"{output_path}"

# Cycles quality
bpy.context.scene.cycles.samples         = {samples}
bpy.context.scene.cycles.use_denoising  = True
bpy.context.scene.cycles.device         = "GPU"

print(f"[Module3-Blender] Starting render: {{render.resolution_x}}x{{render.resolution_y}}, {{scene.frame_end}} frames")
bpy.ops.render.render(animation=True)
print("[Module3-Blender] Render complete")
'''


class BlenderRenderer:
    """
    Drives Blender in headless mode to render a 3D turntable video.
    """

    # Default render settings
    WIDTH         = 1920
    HEIGHT        = 1080
    FPS           = 24
    DURATION_SECS = 8       # 360° in 8 seconds
    SAMPLES       = 64      # Cycles samples per frame

    def __init__(self, specs: dict[str, Any], ifc_path: str, output_dir: Path):
        self.specs      = specs
        self.ifc_path   = ifc_path
        self.output_dir = output_dir
        self.dims       = specs["dimensions"]
        self.part       = specs["part"]

    def is_available(self) -> bool:
        """Check whether Blender is installed and reachable."""
        blender_cmd = self._find_blender()
        if blender_cmd is None:
            return False
        try:
            result = subprocess.run(
                [blender_cmd, "--version"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def render(self) -> Path:
        """Generate the Blender script, run it headlessly, return video path."""
        blender_cmd = self._find_blender()
        if blender_cmd is None:
            raise RuntimeError("Blender executable not found")

        output_path = self.output_dir / f"{self.part['reference']}_blender.mp4"
        script_content = self._build_script(output_path)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(script_content)
            script_path = f.name

        try:
            cmd = [
                blender_cmd,
                "--background",          # headless, no GUI
                "--factory-startup",     # ignore user prefs
                "--python", script_path,
            ]
            logger.info("[Blender] Running: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 min max
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Blender exited with code {result.returncode}.\n"
                    f"stderr: {result.stderr[-1000:]}"
                )
            logger.info("[Blender] stdout tail: %s", result.stdout[-500:])
        finally:
            Path(script_path).unlink(missing_ok=True)

        if not output_path.exists():
            raise RuntimeError(f"Blender completed but output not found: {output_path}")

        return output_path

    # module3/renderer/blender_renderer.py

    def _find_blender(self) -> str | None:
    # 1. Check environment variable first
        env_path = os.environ.get("BLENDER_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

    # 2. Hardcoded common Windows locations (Auto-search)
        common_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        ]
    
        for p in common_paths:
            if os.path.exists(p):
                return p
            
    # 3. Check system PATH
        return shutil.which("blender")

    def _build_script(self, output_path: Path) -> str:
        """Fill the Blender script template with valve-specific values."""
        d            = self.dims
        total_frames = self.FPS * self.DURATION_SECS
        scale        = 0.001   # mm → m for Blender scene units

        return BLENDER_SCRIPT_TEMPLATE.format(
            ifc_path       = str(Path(self.ifc_path).resolve()).replace("\\", "\\\\"),
            output_path    = str(output_path.resolve()).replace("\\", "\\\\"),
            part_reference = self.part["reference"],
            part_name      = self.part["name"],
            # Procedural fallback geometry (all in metres)
            body_radius    = round(d["flange_od_mm"] * 0.75 / 2 * scale, 4),
            flange_radius  = round(d["flange_od_mm"] / 2 * scale, 4),
            flange_thick   = round(d["flange_thickness_mm"] * scale, 4),
            flange_offset  = round((d["face_to_face_mm"] / 2 - d["flange_thickness_mm"] / 2) * scale, 4),
            stem_radius    = round(d["stem_diameter_mm"] / 2 * scale, 4),
            stem_height    = round(60 * scale, 4),
            stem_z         = round((d["body_height_mm"] / 2 + 30) * scale, 4),
            f2f            = round(d["face_to_face_mm"] * scale, 4),
            total_frames   = total_frames,
            fps            = self.FPS,
            width          = self.WIDTH,
            height         = self.HEIGHT,
            samples        = self.SAMPLES,
        )
