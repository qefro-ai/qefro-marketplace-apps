#!/usr/bin/env python3
"""Generate Phase 1–3 Marketplace App YAML from existing Qefro conventions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_phase1
import generate_phase2
import generate_phase3


def main() -> None:
    generate_phase1.generate()
    generate_phase2.generate()
    generate_phase3.generate()
    print("generated 15 Marketplace Apps under apps/")


if __name__ == "__main__":
    main()
