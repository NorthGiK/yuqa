"""Pytest configuration."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
paths = [ROOT]
if SRC.exists():
    paths.insert(0, SRC)
for path in paths:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
