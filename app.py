"""
frozen entry point for the modeller window.

the electron start screen launches this with --project PATH. pyinstaller
freezes this into Minimal3DModeller.exe. the stdout guard stops the status
prints from blowing up in a windowed (no console) build.

from source just use `python main.py`.
"""
import os
import sys


def main() -> None:
    # windowed build has no console, so stdout/stderr can be None -> dump them
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    from main import main as run_modeller
    run_modeller()


if __name__ == "__main__":
    main()
