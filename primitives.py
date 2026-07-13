"""
scene graph nodes: Node (abstract), Primitive, Cube, Sphere, HierarchicalNode,
and the SnowFigure composite example.

layout:
                Node  (abstract)
               /    \\
          Primitive   HierarchicalNode
          /      \\           |
        Cube   Sphere   [child nodes]

every node can draw itself (gl calls inside a push/pop), report its aabb in
world space, and be selected. HierarchicalNode just draws its kids, which is
how the snowman (three stacked spheres) works.
"""

from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import transformations as T
from OpenGL.GL import (
    glPushMatrix, glPopMatrix,
    glMultMatrixf,
    glMaterialfv, glMaterialf,
    GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, GL_SPECULAR, GL_SHININESS,
)
from OpenGL.GLUT import glutSolidCube, glutSolidSphere


# colours by index so cycling is just +1 mod len
COLOURS: List[Tuple[float, float, float]] = [
    (0.95, 0.35, 0.35),   # 0 red
    (0.35, 0.70, 0.95),   # 1 blue
    (0.40, 0.85, 0.45),   # 2 green
    (0.95, 0.75, 0.25),   # 3 yellow
    (0.75, 0.40, 0.95),   # 4 purple
    (0.95, 0.55, 0.25),   # 5 orange
    (0.30, 0.85, 0.80),   # 6 cyan
    (0.95, 0.95, 0.95),   # 7 white
]

SELECTION_COLOUR = (1.0, 1.0, 0.0)  # yellow highlight when selected


class Node(ABC):
    """
    base class for everything in the scene graph.

    colour_index -> index into COLOURS
    selected     -> true while clicked
    translation  -> 4x4 world-space position
    scale_matrix -> 4x4 scale
    """

    def __init__(self) -> None:
        self.colour_index: int = 0
        self.selected: bool = False

        # each node keeps its own transforms; model matrix = translation @ scale
        self.translation: np.ndarray = T.identity()
        self.scale_matrix: np.ndarray = T.identity()

    def translate(self, dx: float, dy: float, dz: float) -> None:
        self.translation = T.translation(dx, dy, dz) @ self.translation

    def scale(self, sx: float, sy: float, sz: float) -> None:
        self.scale_matrix = T.scaling(sx, sy, sz) @ self.scale_matrix

    def model_matrix(self) -> np.ndarray:
        # translate then scale
        return self.translation @ self.scale_matrix

    def render(self) -> None:
        # push our matrix, set the material, let the subclass draw, pop
        glPushMatrix()

        # gl wants column-major so transpose
        m = self.model_matrix().T.astype(np.float32)
        glMultMatrixf(m)

        self._apply_material()
        self._draw()

        glPopMatrix()

    def _apply_material(self) -> None:
        if self.selected:
            colour = SELECTION_COLOUR
        else:
            colour = COLOURS[self.colour_index % len(COLOURS)]

        r, g, b = colour
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [r, g, b, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,            [0.5, 0.5, 0.5, 1.0])
        glMaterialf( GL_FRONT_AND_BACK, GL_SHININESS,           32.0)

    @abstractmethod
    def _draw(self) -> None:
        # subclasses put their actual draw calls here
        ...

    @property
    def aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        # grab the local corners, push them to world space, refit an axis-aligned
        # box. good enough for picking; a tighter box would need mesh traversal.
        local_min, local_max = self._local_aabb()
        corners = _all_corners(local_min, local_max)

        m = self.model_matrix()
        world_corners = [T.apply_matrix(m, c) for c in corners]
        world_corners = np.array(world_corners)

        return world_corners.min(axis=0), world_corners.max(axis=0)

    @abstractmethod
    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        # (min, max) in local space
        ...

    def cycle_colour(self) -> None:
        self.colour_index = (self.colour_index + 1) % len(COLOURS)


class Primitive(Node, ABC):
    # a leaf - no children, just geometry. subclasses only need _draw + _local_aabb
    ...


class Cube(Primitive):
    # unit cube centred at the origin; glutSolidCube(size) draws edge = size
    HALF = 0.5

    def _draw(self) -> None:
        glutSolidCube(1.0)

    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        h = self.HALF
        return np.array([-h, -h, -h]), np.array([h, h, h])


class Sphere(Primitive):
    # unit sphere r=0.5. glutSolidSphere is fine here; a vbo would be nicer
    RADIUS = 0.5

    def _draw(self) -> None:
        glutSolidSphere(self.RADIUS, 24, 16)

    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        r = self.RADIUS
        return np.array([-r, -r, -r]), np.array([r, r, r])


class HierarchicalNode(Node):
    """
    a node that owns child nodes. rendering walks the kids and stacks this
    node's transform on top of theirs. this is the composite pattern:
    Node = component, Primitive subclasses = leaves, this = composite.
    """

    def __init__(self) -> None:
        super().__init__()
        self.children: List[Node] = []

    def add_child(self, node: Node) -> None:
        self.children.append(node)

    def _draw(self) -> None:
        for child in self.children:
            child.render()

    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        if not self.children:
            return np.zeros(3), np.zeros(3)
        # union of the kids' boxes, each nudged by its own translate/scale
        mins, maxs = [], []
        for child in self.children:
            lo, hi = child._local_aabb()
            child_m = child.model_matrix()
            for c in _all_corners(lo, hi):
                p = T.apply_matrix(child_m, c)
                mins.append(p)
                maxs.append(p)
        arr = np.array(mins + maxs)
        return arr.min(axis=0), arr.max(axis=0)


class SnowFigure(HierarchicalNode):
    """
    a snowman - three spheres stacked up (bottom, torso, head). shows off the
    composite: a SnowFigure IS a Node so u can drop it in the scene like any
    other object and the depth-first traversal just handles it.
    """

    def __init__(self) -> None:
        super().__init__()

        # big bottom sphere at the origin
        bottom = Sphere()
        bottom.scale(1.5, 1.5, 1.5)
        bottom.colour_index = 7   # white

        # torso
        torso = Sphere()
        torso.translate(0, 1.1, 0)
        torso.scale(1.0, 1.0, 1.0)
        torso.colour_index = 7

        # small head up top
        head = Sphere()
        head.translate(0, 1.9, 0)
        head.scale(0.65, 0.65, 0.65)
        head.colour_index = 7

        self.add_child(bottom)
        self.add_child(torso)
        self.add_child(head)


def _all_corners(lo: np.ndarray, hi: np.ndarray) -> List[np.ndarray]:
    # all 8 corners of a box, needed to transform an aabb
    return [
        np.array([x, y, z])
        for x in (lo[0], hi[0])
        for y in (lo[1], hi[1])
        for z in (lo[2], hi[2])
    ]
