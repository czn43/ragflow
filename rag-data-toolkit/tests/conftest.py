"""Pytest bootstrap.

Guarantee that the project root is importable regardless of whether tests are
started with `pytest`, `python -m pytest`, an IDE, or from a Windows shell.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
root = str(PROJECT_ROOT)
if root not in sys.path:
    sys.path.insert(0, root)
