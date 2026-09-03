#!/usr/bin/env python3
"""Validate every Marketplace App package against collection conventions.

Includes encoding, $root mapping, flow constants, emits, webhook signature /
identity / topic metadata, auth_type (including basic), entity status_events,
and customer identity placeholders. Every existing package must pass.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
