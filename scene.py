"""
scene graph root + selection/command dispatch.

the Scene is the top container. it holds the root nodes, tracks what's
selected, runs the manipulation commands (translate/scale/colour), and does
picking (ray -> closest node).

it knows nothing about opengl windows, cameras or the glut loop - pure
data/logic. the Viewer calls into it. keeps it easy to serialise, test, or swap
the renderer out.
"""

from __future__ import annotations
import json
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from primitives import Node, Cube, Sphere, SnowFigure
import transformations as T


# kind tag <-> node class for save/load. only top-level types need an entry.
# a SnowFigure rebuilds its own spheres in __init__, so we only store its own
# transform + colour, not its kids.
_KIND_TO_CLASS: Dict[str, type] = {
    "cube": Cube,
    "sphere": Sphere,
    "snowfigure": SnowFigure,
}
_CLASS_TO_KIND: Dict[type, str] = {cls: kind for kind, cls in _KIND_TO_CLASS.items()}


class Scene:
    """
    root of the scene graph. nodes sit in a flat list; HierarchicalNodes hold
    their own kids, so the scene doesn't care how deep things go - traversal is
    recursive.
    """

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self.selected: Optional[Node] = None

        # drop a few objects in so there's something to look at on launch
        self._build_default_scene()

    def _build_default_scene(self) -> None:
        cube = Cube()
        cube.translate(-1.5, 0, 0)
        cube.colour_index = 1
        self.nodes.append(cube)

        sphere = Sphere()
        sphere.translate(1.5, 0, 0)
        sphere.colour_index = 2
        self.nodes.append(sphere)

        snowman = SnowFigure()
        snowman.translate(0, -0.5, 0)
        self.nodes.append(snowman)

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def remove_selected(self) -> None:
        if self.selected is not None and self.selected in self.nodes:
            self.nodes.remove(self.selected)
            self.selected = None

    def render(self) -> None:
        # depth-first; each node push/pops its own matrix so transforms don't leak
        for node in self.nodes:
            node.render()

    def pick(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> Optional[Node]:
        """
        pick the node whose box the ray hits first.

        for each node: get its world aabb, run the slab test, keep the smallest
        hit distance. we use aabb not exact triangle picking because it's way
        simpler and plenty accurate when objects aren't overlapping tightly -
        exact picking would need a full bvh.
        """
        from transformations import ray_aabb_intersect

        best_t = np.inf
        best_node: Optional[Node] = None

        for node in self.nodes:
            aabb_min, aabb_max = node.aabb
            hit, t = ray_aabb_intersect(ray_origin, ray_dir, aabb_min, aabb_max)
            if hit and t < best_t:
                best_t = t
                best_node = node

        # swap selection
        if self.selected is not None:
            self.selected.selected = False

        self.selected = best_node
        if best_node is not None:
            best_node.selected = True

        return best_node

    def deselect_all(self) -> None:
        if self.selected:
            self.selected.selected = False
        self.selected = None

    def move_selected(self, dx: float, dy: float, dz: float) -> None:
        if self.selected:
            self.selected.translate(dx, dy, dz)

    def scale_selected(self, factor: float) -> None:
        if self.selected:
            self.selected.scale(factor, factor, factor)

    def cycle_colour_selected(self) -> None:
        if self.selected:
            self.selected.cycle_colour()

    def add_cube(self, x: float = 0, y: float = 0, z: float = 0) -> Cube:
        node = Cube()
        node.translate(x, y, z)
        self.add_node(node)
        return node

    def add_sphere(self, x: float = 0, y: float = 0, z: float = 0) -> Sphere:
        node = Sphere()
        node.translate(x, y, z)
        self.add_node(node)
        return node

    # one serialisation layer used by both undo/redo and file save/load

    def to_dict(self) -> Dict[str, Any]:
        # dump the scene to plain builtins. each node -> kind + its two matrices
        # + colour. json-friendly, so undo snapshots and save files are identical.
        nodes = []
        for node in self.nodes:
            kind = _CLASS_TO_KIND.get(type(node))
            if kind is None:
                continue  # can't persist this type, skip it
            nodes.append({
                "kind": kind,
                "translation": node.translation.tolist(),
                "scale": node.scale_matrix.tolist(),
                "colour_index": node.colour_index,
            })
        return {"nodes": nodes}

    def from_dict(self, data: Dict[str, Any]) -> None:
        # replace the scene with a snapshot from to_dict()
        self.deselect_all()
        rebuilt: List[Node] = []
        for entry in data.get("nodes", []):
            cls = _KIND_TO_CLASS.get(entry.get("kind"))
            if cls is None:
                continue
            node = cls()
            node.translation = np.array(entry["translation"], dtype=np.float64)
            node.scale_matrix = np.array(entry["scale"], dtype=np.float64)
            node.colour_index = int(entry.get("colour_index", 0))
            rebuilt.append(node)
        self.nodes = rebuilt
        self.selected = None

    def save_to_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    def load_from_file(self, path: str) -> bool:
        # returns false if the file's missing/broken, and leaves the scene alone
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return False
        self.from_dict(data)
        return True
