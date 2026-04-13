#!/usr/bin/env python3
"""
run_module3.py

Standalone runner for Module 3 — Video Generation.

Usage:
    python run_module3.py
    python run_module3.py --state data/dummy/pipeline_state.json
    python run_module3.py --renderer pillow   # force a specific renderer
    python run_module3.py --renderer manim
    python run_module3.py --renderer blender
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from module3.agent.video_agent import run_standalone, run_video_generation


def main():
    parser = argparse.ArgumentParser(description="Run Module 3 Video Generation")
    parser.add_argument(
        "--state",
        default="data/dummy/pipeline_state.json",
        help="Path to the pipeline state JSON (Module 1+2 output or dummy)",
    )
    parser.add_argument(
        "--renderer",
        choices=["auto", "blender", "manim", "pillow"],
        default="auto",
        help="Force a specific renderer (default: auto = best available)",
    )
    args = parser.parse_args()

    state_path = Path(args.state)
    if not state_path.exists():
        print(f"[ERROR] State file not found: {state_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  INDUSTRIE IA — Module 3: Video Generation")
    print(f"{'='*60}")
    print(f"  Input state : {state_path}")
    print(f"  Renderer    : {args.renderer}")
    print(f"{'='*60}\n")

    with open(state_path) as f:
        state = json.load(f)

    # Force renderer if specified
    if args.renderer != "auto":
        state["_force_renderer"] = args.renderer

    result = run_video_generation(state)

    video_path    = result.get("video_output", "")
    renderer_used = result.get("video_renderer_used", "none")
    errors        = result.get("video_errors", [])

    if video_path:
        size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        print(f"\n✅ Video generated via [{renderer_used.upper()}]")
        print(f"   {video_path}  ({size_mb:.1f} MB)")
    else:
        print("\n❌ No video generated")

    if errors:
        print("\n⚠️  Errors / warnings:")
        for e in errors:
            print(f"   • {e}")

    print()
    return 0 if video_path else 1


if __name__ == "__main__":
    sys.exit(main())
