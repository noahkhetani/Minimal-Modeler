"""
opens the 3d modeller window.

the start screen (electron app) launches this with --project, but u can also
just run `python main.py` to get the default scene, or `--project path.json`
to open a specific one.
"""

import argparse
import os
import sys

# make sure this dir is importable if u run it from somewhere else
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_keybinds
from viewer import Viewer


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal 3D Modeller")
    parser.add_argument("--project", metavar="PATH",
                        help="path to a project .json scene file to open")
    args = parser.parse_args()

    viewer = Viewer(
        width=960, height=640, title="Minimal 3D Modeller",
        keybinds=load_keybinds(),
        project_path=args.project,
    )
    viewer.run()


if __name__ == "__main__":
    main()
