#!/usr/bin/env python3
"""
run_module2.py

Standalone runner for Module 2 — CAD Generation.
Use this during development without the full LangGraph pipeline.

Usage:
    python run_module2.py
    python run_module2.py --specs data/dummy/valve_dn100_pn40.json
    python run_module2.py --specs /path/to/your/specs.json
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

# Allow running from the module2/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from module2.agent.cad_agent import run_standalone


def main():
    parser = argparse.ArgumentParser(description="Run Module 2 CAD generation")
    parser.add_argument(
        "--specs",
        default="data/dummy/valve_dn100_pn40.json",
        help="Path to the JSON specs file (Module 1 output or dummy data)",
    )
    args = parser.parse_args()

    specs_path = Path(args.specs)
    if not specs_path.exists():
        print(f"[ERROR] Specs file not found: {specs_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  INDUSTRIE IA — Module 2: CAD Generation")
    print(f"{'='*60}")
    print(f"  Input specs: {specs_path}")
    print(f"{'='*60}\n")

    result = run_standalone(specs_path)

    outputs = result.get("cad_outputs", {})
    errors = result.get("cad_errors", [])

    if outputs:
        print("\n✅ Generated files:")
        for fmt, path in outputs.items():
            size_kb = Path(path).stat().st_size / 1024
            print(f"   [{fmt.upper():>4}]  {path}  ({size_kb:.1f} KB)")

    if errors:
        print("\n⚠️  Errors:")
        for err in errors:
            print(f"   • {err}")

    print()
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
