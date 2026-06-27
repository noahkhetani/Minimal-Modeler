"""
primitives.py — Scene graph nodes: abstract Node, Primitive, Cube, Sphere,
HierarchicalNode, and the composite SnowFigure example.

Scene Graph (Composite Pattern)
--------------------------------
                Node  (abstract)
               /    \\
          Primitive   HierarchicalNode
          /      \\           |
        Cube   Sphere   [list of child Nodes]

Every Node knows how to:
  - render itself (OpenGL draw calls inside a matrix push/pop)
  - report its AABB (axis-aligned bounding box) in world space
  - respond to selection

The HierarchicalNode delegates rendering to its children, enabling
arbitrary hierarchical objects like the SnowFigure (three stacked spheres).
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
    GL_COMPILE, GL_RENDER,
    glCallList, glNewList, glEndList, glGenLists,
)
from OpenGL.GLU import gluSphere, gluNewQuadric
from OpenGL.GLUT import glutSolidCube, glutSolidSphere


# ---------------------------------------------------------------------------
# Colour palette — indexed by an integer so colour-cycling is trivial
# ---------------------------------------------------------------------------

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

SELECTION_COLOUR = (1.0, 1.0, 0.0)  # bright yellow highlight when selected


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class Node(ABC):
    """
    Base class for all objects in the scene graph.

    Attributes:
        colour_index  : index into COLOURS palette
        selected      : True while the user has clicked on this node
        translation   : 4×4 translation matrix (world-space position)
        scale_matrix  : 4×4 scale matrix
    """

    def __init__(self) -> None:
        self.colour_index: int = 0
        self.selected: bool = False

        # Each node carries its own transform matrices.
        # The combined model matrix is:  translation @ scale_matrix
        self.translation: np.ndarray = T.identity()
        self.scale_matrix: np.ndarray = T.identity()

    # ------------------------------------------------------------------
    # Transform helpers
    # ------------------------------------------------------------------

    def translate(self, dx: float, dy: float, dz: float) -> None:
        """Accumulate a translation in world space."""
        self.translation = T.translation(dx, dy, dz) @ self.translation

    def scale(self, sx: float, sy: float, sz: float) -> None:
        """Accumulate a scale."""
        self.scale_matrix = T.scaling(sx, sy, sz) @ self.scale_matrix

    def model_matrix(self) -> np.ndarray:
        """Combined model→world transform: translate then scale."""
        return self.translation @ self.scale_matrix

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> None:
        """
        Push the node's model matrix, apply colour/selection material,
        call the subclass draw method, then pop.
        """
        glPushMatrix()

        # OpenGL expects column-major (Fortran order) so we transpose.
        m = self.model_matrix().T.astype(np.float32)
        glMultMatrixf(m)

        self._apply_material()
        self._draw()

        glPopMatrix()

    def _apply_material(self) -> None:
        """Set OpenGL material properties for the current node."""
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
        """Subclasses implement the actual draw calls here."""

    # ------------------------------------------------------------------
    # AABB — Axis-Aligned Bounding Box in world space
    # ------------------------------------------------------------------

    @property
    def aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return (min_pt, max_pt) in world space.

        We compute the local AABB corners, transform them all into world
        space, then re-fit an axis-aligned box.  This is fast and sufficient
        for picking; a tighter box would require mesh-level traversal.
        """
        local_min, local_max = self._local_aabb()
        corners = _all_corners(local_min, local_max)

        m = self.model_matrix()
        world_corners = [T.apply_matrix(m, c) for c in corners]
        world_corners = np.array(world_corners)

        return world_corners.min(axis=0), world_corners.max(axis=0)

    @abstractmethod
    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (min, max) in local/model space."""

    # ------------------------------------------------------------------
    # Colour cycling
    # ------------------------------------------------------------------

    def cycle_colour(self) -> None:
        self.colour_index = (self.colour_index + 1) % len(COLOURS)


# ---------------------------------------------------------------------------
# Primitive leaf node
# ---------------------------------------------------------------------------

class Primitive(Node, ABC):
    """
    A leaf in the scene graph — no children, just geometry.
    Subclasses only need to define _draw() and _local_aabb().
    """


# ---------------------------------------------------------------------------
# Cube
# ---------------------------------------------------------------------------

class Cube(Primitive):
    """
    Unit cube (side length = 1, centred at origin in local space).

    GLUT's glutSolidCube(size) draws a cube of edge *size*.
    """

    HALF = 0.5   # half-extent in each axis for a unit cube

    def _draw(self) -> None:
        glutSolidCube(1.0)

    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        h = self.HALF
        return np.array([-h, -h, -h]), np.array([h, h, h])


# ---------------------------------------------------------------------------
# Sphere
# ---------------------------------------------------------------------------

class Sphere(Primitive):
    """
    Unit sphere (radius = 0.5) centred at origin in local space.

    We use GLUT's glutSolidSphere for simplicity.  A higher-quality
    version would use a VBO with pre-tessellated geometry.
    """

    RADIUS = 0.5

    def _draw(self) -> None:
        glutSolidSphere(self.RADIUS, 24, 16)

    def _local_aabb(self) -> Tuple[np.ndarray, np.ndarray]:
        r = self.RADIUS
        return np.array([-r, -r, -r]), np.array([r, r, r])


# ---------------------------------------------------------------------------
# HierarchicalNode — the Composite
# ---------------------------------------------------------------------------

class HierarchicalNode(Node):
    """
    A node that owns a list of child nodes.

    Rendering traverses children in order, applying this node's transform
    on top of whatever transforms the children already carry.

    This is the core of the Composite Design Pattern:
        - Component = Node
        - Leaf       = Primitive subclasses
        - Composite  = HierarchicalNode
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
        # Merge children's world AABBs into a single AABB.
        # Note: children's aabb is already in their own world space.
        # We need local AABB, so we use untransformed bounding union.
        mins, maxs = [], []
        for child in self.children:
            lo, hi = child._local_aabb()
            # Account for child's own translation/scale in local coords
            child_m = child.model_matrix()
            for c in _all_corners(lo, hi):
                p = T.apply_matrix(child_m, c)
                mins.append(p)
                maxs.append(p)
        arr = np.array(mins + maxs)
        return arr.min(axis=0), arr.max(axis=0)


# ---------------------------------------------------------------------------
# SnowFigure — example composite object
# ---------------------------------------------------------------------------

class SnowFigure(HierarchicalNode):
    """
    A classic snowman built from three spheres: bottom, torso, head.

    This demonstrates the Composite Pattern: SnowFigure IS a Node, so it
    can be added to a scene just like any primitive.  The scene-graph
    traversal is depth-first and fully transparent to the Scene.
    """

    def __init__(self) -> None:
        super().__init__()

        # Bottom sphere — large, sits at origin
        bottom = Sphere()
        bottom.scale(1.5, 1.5, 1.5)
        bottom.colour_index = 7   # white

        # Middle / torso sphere
        torso = Sphere()
        torso.translate(0, 1.1, 0)
        torso.scale(1.0, 1.0, 1.0)
        torso.colour_index = 7

        # Head — small, at the top
        head = Sphere()
        head.translate(0, 1.9, 0)
        head.scale(0.65, 0.65, 0.65)
        head.colour_index = 7

        self.add_child(bottom)
        self.add_child(torso)
        self.add_child(head)


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _all_corners(lo: np.ndarray, hi: np.ndarray) -> List[np.ndarray]:
    """Generate all 8 corners of an AABB — needed for AABB transform."""
    return [
        np.array([x, y, z])
        for x in (lo[0], hi[0])
        for y in (lo[1], hi[1])
        for z in (lo[2], hi[2])
    ]
