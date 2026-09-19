#!/usr/bin/env python3
"""Device-terminal launcher for deployed PRISM System Administrator management.

Run from the repository root:
    python manage_admin.py --help
"""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "backend" / "scripts" / "manage_admin.py"),
    run_name="__main__",
)
