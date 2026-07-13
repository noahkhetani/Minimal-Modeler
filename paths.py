"""
where user data (keybinds, projects) lives.

from source we just keep it in the repo folder (it's gitignored anyway). once
it's frozen into an installed exe, the install dir under program files isn't
writable, so we fall back to %APPDATA%\\Minimal3DModeller.
"""
from __future__ import annotations

import os
import sys


def user_data_dir() -> str:
    # give back a writable dir for keybinds/projects, making it if needed
    if getattr(sys, "frozen", False):  # inside a pyinstaller bundle
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "Minimal3DModeller")
    else:
        path = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(path, exist_ok=True)
    return path
