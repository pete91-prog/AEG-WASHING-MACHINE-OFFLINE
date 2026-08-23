"""Load the dishwasher modules without importing Home Assistant."""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "aeg_fse73768p"

if "aeg_fse73768p" not in sys.modules:
    pkg = types.ModuleType("aeg_fse73768p")
    pkg.__path__ = [str(ROOT)]
    pkg.__package__ = "aeg_fse73768p"
    sys.modules["aeg_fse73768p"] = pkg
