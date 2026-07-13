"""
headless tests for the non-opengl stuff - the bits that don't need a gl
context or a window: scene setup, json serialisation (shared by save/load and
undo/redo), the undo/redo flow, and the ray-aabb picking math.

run:  python tests/test_core.py
"""
import os
import sys

import numpy as np

# so it runs from the repo root or the tests/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config                                 # noqa: E402
from scene import Scene                       # noqa: E402
from primitives import SnowFigure             # noqa: E402
from transformations import ray_aabb_intersect  # noqa: E402


def approx_eq(a, b) -> bool:
    return np.allclose(np.array(a), np.array(b))


def test_default_scene() -> None:
    s = Scene()
    assert len(s.nodes) == 3, f"expected 3 default nodes, got {len(s.nodes)}"


def test_serialisation_round_trip() -> None:
    s = Scene()
    s.add_cube(2, 0, 0)
    s.nodes[-1].cycle_colour()
    snap = s.to_dict()
    assert len(snap["nodes"]) == 4

    restored = Scene()
    restored.from_dict(snap)
    assert len(restored.nodes) == 4, "node count lost on round-trip"
    for a, b in zip(s.nodes, restored.nodes):
        assert type(a) is type(b), f"kind changed: {type(a)} vs {type(b)}"
        assert approx_eq(a.translation, b.translation), "translation lost"
        assert approx_eq(a.scale_matrix, b.scale_matrix), "scale lost"
        assert a.colour_index == b.colour_index, "colour lost"

    # snowman should come back as a composite with its 3 spheres rebuilt
    assert any(isinstance(n, SnowFigure) and len(n.children) == 3
               for n in restored.nodes), "SnowFigure not rebuilt with 3 children"


def test_undo_redo() -> None:
    s = Scene()
    undo, redo = [], []

    def snapshot() -> None:
        undo.append(s.to_dict())
        redo.clear()

    snapshot()
    s.add_sphere(5, 5, 5)
    assert len(s.nodes) == 4

    redo.append(s.to_dict())          # undo
    s.from_dict(undo.pop())
    assert len(s.nodes) == 3, "undo did not restore node count"

    undo.append(s.to_dict())          # redo
    s.from_dict(redo.pop())
    assert len(s.nodes) == 4, "redo did not re-apply"


def test_save_load(tmp_path: str = "test_scene.json") -> None:
    s = Scene()
    s.save_to_file(tmp_path)
    try:
        loaded = Scene()
        assert loaded.load_from_file(tmp_path)
        assert len(loaded.nodes) == len(s.nodes), "file save/load mismatch"
    finally:
        os.remove(tmp_path)
    assert Scene().load_from_file("does_not_exist.json") is False, \
        "missing file should return False, not raise"


def test_ray_aabb() -> None:
    lo, hi = np.array([-1, -1, -1.0]), np.array([1, 1, 1.0])
    hit, t = ray_aabb_intersect(np.array([0, 0, 5.0]),
                                np.array([0, 0, -1.0]), lo, hi)
    assert hit and abs(t - 4.0) < 1e-6, f"expected hit at t=4, got hit={hit} t={t}"

    miss, _ = ray_aabb_intersect(np.array([5, 5, 5.0]),
                                 np.array([0, 0, -1.0]), lo, hi)
    assert not miss, "ray that misses the box reported a hit"


def test_keybinds_unique() -> None:
    kb = config.load_keybinds()
    # every action has a key, and no two share one
    assert set(kb) == set(dict(config.ACTION_LABELS)), "action/label mismatch"
    assert len(set(kb.values())) == len(kb), "duplicate key bindings"


def main() -> None:
    tests = [
        test_default_scene,
        test_serialisation_round_trip,
        test_undo_redo,
        test_save_load,
        test_ray_aabb,
        test_keybinds_unique,
    ]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
