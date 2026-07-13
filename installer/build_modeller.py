#!/usr/bin/env python
"""
freeze the python modeller so the desktop app can ship it.

builds a onedir modeller with pyinstaller and drops it in
desktop/resources/modeller/, where electron-builder grabs it via extraResources
(see desktop/electron-builder.yml). the start screen then spawns
resources/modeller/Minimal3DModeller.exe --project ...

usage:
    pip install pyinstaller
    python installer/build_modeller.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BUILD = os.path.join(REPO, "build_pkg")                       # scratch, gitignored
DIST = os.path.join(BUILD, "dist_modeller")
OUT = os.path.join(REPO, "desktop", "resources", "modeller")  # what electron-builder bundles


def main() -> None:
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed",
        "--name", "Minimal3DModeller", "--collect-all", "OpenGL",
        "--distpath", DIST,
        "--workpath", os.path.join(BUILD, "build_modeller"),
        "--specpath", BUILD,
        os.path.join(REPO, "app.py"),
    ])

    src = os.path.join(DIST, "Minimal3DModeller")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    shutil.copytree(src, OUT)
    print("\nmodeller bundled to:", OUT)


if __name__ == "__main__":
    main()
