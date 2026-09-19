#!/usr/bin/env python3
"""Device-terminal launcher for PRISM PostgreSQL Database Initialization & Reinitialization.

Run from the repository root:
    python reinit_db.py --help
    python reinit_db.py --sync
    python reinit_db.py --clean
    python reinit_db.py
"""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "backend" / "scripts" / "reinit_db.py"),
    run_name="__main__",
)
