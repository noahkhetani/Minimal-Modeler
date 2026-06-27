"""
scene.py — Scene graph root and selection/command dispatch.

The Scene is the top-level container.  It:
  1. Holds all root-level nodes.
  2. Tracks the currently selected node.
  3. Dispatches manipulation commands (translate, scale, colour-cycle).
  4. Handles picking — converting a ray into the closest selected node.

Architecture note
-----------------
The Scene does NOT know about OpenGL windows, cameras, or the GLUT event
loop.  It is a pure data/logic layer.  The Viewer calls into it to render
and to relay interaction commands.  This separation makes it easy to
serialise, test, or swap the renderer independently.
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional, Tuple

from primitives import Node, Cube, Sphere, SnowFigure
import transformations as T


class Scene:
    """
    Root of the scene graph.

    Nodes are stored in a flat list at the top level; HierarchicalNodes
    carry their own children internally.  The Scene therefore has no
    awareness of hierarchy depth — traversal is fully recursive.
    """

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self.selected: Optional[Node] = None

        # Populate with a small starting scene so the user sees something
        # immediately on launch.
        self._build_default_scene()

    # ------------------------------------------------------------------
    # Scene construction
    # ------------------------------------------------------------------

    def _build_default_scene(self) -> None:
        """Place a few objects into the world at startup."""
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
        """Add an arbitrary node to the scene."""
        self.nodes.append(node)

    def remove_selected(self) -> None:
        """Delete the currently selected node from the scene."""
        if self.selected is not None and self.selected in self.nodes:
            self.nodes.remove(self.selected)
            self.selected = None

    # ------------------------------------------------------------------
    # Rendering — delegate to each node
    # ------------------------------------------------------------------

    def render(self) -> None:
        """
        Depth-first render traversal.

        Each node renders itself (with its children, if composite) inside
        its own glPushMatrix / glPopMatrix block so transforms don't leak.
        """
        for node in self.nodes:
            node.render()

    # ------------------------------------------------------------------
    # Picking — ray vs. AABB for all nodes
    # ------------------------------------------------------------------

    def pick(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> Optional[Node]:
        """
        Select the node whose bounding box is closest along the ray.

        Algorithm:
            For every node, compute its world-space AABB.
            Run a ray-AABB slab test (see transformations.ray_aabb_intersect).
            Keep track of the minimum hit distance t.
            The node with the smallest t is selected.

        Why AABB and not exact mesh intersection?
        - For a modeller at this scale, AABB is fast enough and simple.
        - Exact triangle picking requires a full BVH and mesh traversal.
        - AABB misses are acceptable when objects don't overlap tightly.
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

        # Deselect old, select new
        if self.selected is not None:
            self.selected.selected = False

        self.selected = best_node
        if best_node is not None:
            best_node.selected = True

        return best_node

    def deselect_all(self) -> None:
        """Clear selection without picking anything new."""
        if self.selected:
            self.selected.selected = False
        self.selected = None

    # ------------------------------------------------------------------
    # Manipulation commands — applied to the selected node
    # ------------------------------------------------------------------

    def move_selected(self, dx: float, dy: float, dz: float) -> None:
        """Translate the selected node."""
        if self.selected:
            self.selected.translate(dx, dy, dz)

    def scale_selected(self, factor: float) -> None:
        """Uniformly scale the selected node."""
        if self.selected:
            self.selected.scale(factor, factor, factor)

    def cycle_colour_selected(self) -> None:
        """Advance the selected node's colour by one step."""
        if self.selected:
            self.selected.cycle_colour()

    # ------------------------------------------------------------------
    # Add primitives from the keyboard
    # ------------------------------------------------------------------

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
