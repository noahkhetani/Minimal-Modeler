"""
global, editable keybinds.

stored as a flat {action: key} map in keybinds.json. the start screen edits
them, the modeller reads them. if the file's missing or busted we fall back to
DEFAULT_KEYBINDS so the app still starts.

keys are single chars and case sensitive - 'a' and 'A' (shift+a) are different,
same as how glut reports ascii keys.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from paths import user_data_dir

# keybind file lives in the user data dir (repo root from source, %APPDATA% installed)
CONFIG_PATH = os.path.join(user_data_dir(), "keybinds.json")

# action -> default single char key
DEFAULT_KEYBINDS: Dict[str, str] = {
    "add_cube": "a",
    "add_sphere": "A",
    "scale_up": "s",
    "scale_down": "S",
    "cycle_colour": "c",
    "delete": "d",
    "undo": "z",
    "redo": "Z",
    "save": "o",
    "load": "l",
    "wireframe": "w",
    "reset_camera": "r",
    "move_near": "[",
    "move_far": "]",
    "quit": "q",
}

# (action, label) in order - drives the keybind table in the start screen
ACTION_LABELS: List[Tuple[str, str]] = [
    ("add_cube", "Add cube"),
    ("add_sphere", "Add sphere"),
    ("scale_up", "Scale selected up"),
    ("scale_down", "Scale selected down"),
    ("cycle_colour", "Cycle colour"),
    ("delete", "Delete selected"),
    ("undo", "Undo"),
    ("redo", "Redo"),
    ("save", "Save project"),
    ("load", "Reload project"),
    ("wireframe", "Toggle wireframe"),
    ("reset_camera", "Reset camera"),
    ("move_near", "Move toward camera"),
    ("move_far", "Move away from camera"),
    ("quit", "Quit"),
]


def load_keybinds() -> Dict[str, str]:
    # saved keybinds merged over the defaults (defaults win for anything missing)
    merged = dict(DEFAULT_KEYBINDS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return merged
    if isinstance(data, dict):
        for action, key in data.items():
            if action in merged and isinstance(key, str) and len(key) == 1:
                merged[action] = key
    return merged


def save_keybinds(keybinds: Dict[str, str]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(keybinds, fh, indent=2)


def reset_keybinds() -> Dict[str, str]:
    # put the defaults back and save them
    fresh = dict(DEFAULT_KEYBINDS)
    save_keybinds(fresh)
    return fresh
