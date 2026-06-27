"""
main.py — Entry point for the 3D modeller.

Run:
    python main.py

Keyboard shortcuts
------------------
    q / Esc       Quit
    a             Add cube at origin
    A             Add sphere at origin
    s             Scale selected up  (×1.1)
    S             Scale selected down (÷1.1)
    c             Cycle colour of selected object
    d             Delete selected object
    w             Toggle wireframe mode
    r             Reset camera

Mouse
-----
    Left-click    Select object (ray-AABB picking)
    Left-drag     Rotate scene  (trackball)
    Right-drag    Pan camera
    Scroll wheel  Zoom in / out

Arrow keys
----------
    ← → ↑ ↓      Move selected object in XY plane
"""

import sys
import os

# Make sure the 3d-modeller directory is on the path when run from elsewhere
sys.path.insert(0, os.path.dirname(__file__))

from viewer import Viewer


def main() -> None:
    viewer = Viewer(width=960, height=640, title="Minimal 3D Modeller")
    viewer.run()


if __name__ == "__main__":
    main()
