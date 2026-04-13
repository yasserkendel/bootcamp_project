# Module 3 — HD Presentation Video

**Part of: INDUSTRIE IA — Bootcamp IA 2026**

Takes the pipeline state from Module 2 (CAD outputs + specs) and generates
a full HD presentation video of the industrial valve.

---

## Renderer Tiers

| Tier | Renderer | Quality | Install |
|------|----------|---------|---------|
| 1 (fallback) | **Pillow + imageio** | Good — 2D animated frames | `pip install pillow imageio imageio-ffmpeg` |
| 2 | **Manim** | Great — programmatic technical animation | `pip install manim` + LaTeX |
| 3 (best) | **Blender** | Photorealistic 3D turntable | Install Blender + BlenderBIM addon |

The agent automatically tries Blender → Manim → Pillow, using the best available.

---

## Pipeline position

```
Module 2 (CAD → DXF + IFC)
        │
        ▼
Module 3 (Video) ◀─── YOU ARE HERE
        │
        ▼
Module 4 (Sourcing)
```

**Reads:** `state["specs"]`, `state["cad_outputs"]["ifc"]`
**Writes:** `state["video_output"]`, `state["video_renderer_used"]`

---

## Quick start

```bash
pip install -r requirements.txt

# Auto renderer (best available)
python run_module3.py

# Force a specific renderer
python run_module3.py --renderer pillow
python run_module3.py --renderer manim
python run_module3.py --renderer blender
```

---

## Tests

```bash
cd module3
python -m pytest tests/ -v
python -m pytest tests/ -v --cov=module3 --cov-report=term-missing
```

Blender/Manim tests auto-skip if those tools aren't installed.
Pillow tests always run.

---

## Blender setup (for best quality)

1. Download Blender from https://www.blender.org/download/
2. Install BlenderBIM addon from https://blenderbim.org/ (needed for IFC import)
3. Either add Blender to your PATH, or set the env variable:
   ```
   set BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.0\blender.exe
   ```

---

## File structure

```
module3/
├── agent/
│   └── video_agent.py          # LangGraph node + renderer selection logic
├── renderer/
│   ├── blender_renderer.py     # Tier 3: Blender headless 3D render
│   ├── manim_renderer.py       # Tier 2: Manim technical animation
│   └── pillow_renderer.py      # Tier 1: Pillow fallback (always works)
├── utils/
│   └── validators.py
├── tests/
│   └── test_module3.py         # Test suite — Blender/Manim skip if absent
├── data/dummy/
│   └── pipeline_state.json     # Mock Module 1+2 state for dev
├── outputs/                    # Generated MP4 files (git-ignored)
├── conftest.py
├── run_module3.py
├── requirements.txt
└── README.md
```

---

## LangGraph wiring

```python
from module3.agent.video_agent import run_video_generation

graph.add_node("module3_video", run_video_generation)
graph.add_edge("module2_cad", "module3_video")
graph.add_edge("module3_video", "module4_sourcing")
```
