"""
viewer.py — Window creation, OpenGL setup, camera, and the render loop.

The Viewer is the boundary between the OS/OpenGL driver and our scene.
It is responsible for:
  - Creating the GLUT window
  - Setting the projection matrix
  - Handling camera (model-view) transformations
  - Clearing buffers and triggering render passes
  - Connecting the Interaction event bus to Scene commands

Coordinate spaces in this renderer
------------------------------------
Local (Model) Space
    ↓  model_matrix (per node)
World Space
    ↓  camera transform (rotation + translation applied here)
View (Eye) Space
    ↓  gluPerspective projection
Clip Space → Normalised Device Coords → Screen/Pixel Space

The "camera" in a classic OpenGL scene is just the inverse of the world
transform applied to everything else.  We never move the camera; we move
the world — which is mathematically identical.

Trackball rotation
-------------------
A trackball simulates rotating a virtual sphere beneath your hand.
Moving the mouse horizontally rotates the scene around the Y axis;
vertically around the X axis.  This avoids gimbal lock because we
accumulate rotation as a matrix product, not as three Euler angles.
Gimbal lock occurs when two rotation axes align, removing a degree of
freedom.  Our matrix accumulation always preserves all three axes.
"""

from __future__ import annotations
import sys
import numpy as np

from OpenGL.GL import (
    glClear, glClearColor, glEnable, glDisable,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LIGHTING, GL_LIGHT0, GL_LIGHT1,
    GL_NORMALIZE, GL_COLOR_MATERIAL,
    glMatrixMode, glLoadIdentity, glMultMatrixf,
    GL_PROJECTION, GL_MODELVIEW,
    glViewport, glFlush,
    glPushMatrix, glPopMatrix,
    glLineWidth, glBegin, glEnd, glVertex3f, glColor3f,
    GL_LINES,
    glLightfv,
    GL_POSITION, GL_DIFFUSE, GL_AMBIENT, GL_SPECULAR,
    GL_LINE_BIT, glPushAttrib, glPopAttrib,
    glPolygonMode, GL_FRONT_AND_BACK, GL_LINE, GL_FILL,
)
from OpenGL.GLU import gluPerspective, gluUnProject
from OpenGL.GLUT import (
    glutInit, glutInitDisplayMode, glutInitWindowSize,
    glutCreateWindow, glutDisplayFunc, glutReshapeFunc,
    glutMainLoop, glutSwapBuffers, glutPostRedisplay,
    GLUT_DOUBLE, GLUT_RGB, GLUT_DEPTH,
    glutGet, GLUT_WINDOW_WIDTH, GLUT_WINDOW_HEIGHT,
)

import transformations as T
from interaction import Interaction
from scene import Scene


class Viewer:
    """
    Manages the OpenGL window and coordinates rendering.

    Parameters
    ----------
    width, height : initial window dimensions
    title         : window title bar text
    """

    # Field of view for the perspective projection (degrees)
    FOV = 45.0
    NEAR_CLIP = 0.1
    FAR_CLIP  = 1000.0

    # Scroll zoom step — how much we move the camera along Z per wheel tick
    ZOOM_STEP = 0.5

    def __init__(self, width: int = 900, height: int = 600, title: str = "3D Modeller") -> None:
        self.width  = width
        self.height = height

        # Camera / world rotation accumulator (trackball-style)
        # We accumulate rotations as 4×4 matrices.  No Euler angles = no gimbal.
        self._rotation: np.ndarray = T.identity()

        # Camera Z distance (zoom)
        self._camera_z: float = -7.0

        # World translation (right-drag to pan)
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0

        # Wireframe toggle
        self._wireframe: bool = False

        # Undo stack — list of scene state snapshots (simple approach)
        self._undo_stack: list = []

        self._init_glut(title)
        self._init_gl()

        self.scene       = Scene()
        self.interaction = Interaction()

        self._connect_events()

    # ------------------------------------------------------------------
    # GLUT / OpenGL initialisation
    # ------------------------------------------------------------------

    def _init_glut(self, title: str) -> None:
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
        glutInitWindowSize(self.width, self.height)
        glutCreateWindow(title.encode())

        glutDisplayFunc(self._render)
        glutReshapeFunc(self._reshape)

    def _init_gl(self) -> None:
        """Configure fixed-function OpenGL state once at startup."""
        glClearColor(0.15, 0.15, 0.18, 1.0)   # dark background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)                 # auto-normalise normals after scaling
        glEnable(GL_LIGHTING)

        # Two-point lighting: a key light and a soft fill
        self._setup_lights()

    def _setup_lights(self) -> None:
        """
        Key light (LIGHT0) from upper-left; fill light (LIGHT1) from right.
        Positions are in homogeneous coordinates: w=1 → positional, w=0 → directional.
        """
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 8.0, 5.0, 0.0])    # directional
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.97, 0.90, 1.0])  # warm white
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.15, 0.15, 0.18, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.6, 0.6, 0.6, 1.0])

        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_POSITION, [-5.0, 3.0, -3.0, 0.0])  # fill, opposite side
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.25, 0.30, 0.40, 1.0]) # cool blue fill
        glLightfv(GL_LIGHT1, GL_AMBIENT,  [0.0,  0.0,  0.0,  1.0])
        glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0,  0.0,  0.0,  1.0])

    # ------------------------------------------------------------------
    # Reshape — keep aspect ratio correct when window is resized
    # ------------------------------------------------------------------

    def _reshape(self, width: int, height: int) -> None:
        self.width  = width
        self.height = max(height, 1)  # avoid divide-by-zero
        glViewport(0, 0, self.width, self.height)
        self._set_projection()

    def _set_projection(self) -> None:
        """Set up a perspective projection matrix."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width / self.height
        gluPerspective(self.FOV, aspect, self.NEAR_CLIP, self.FAR_CLIP)
        glMatrixMode(GL_MODELVIEW)

    # ------------------------------------------------------------------
    # Main render loop
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Called by GLUT every frame."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # ---- Camera transform (moves the world, not the camera) ----
        # 1. Pull back along Z so we see the scene
        from OpenGL.GL import glTranslatef, glScalef
        glTranslatef(self._pan_x, self._pan_y, self._camera_z)

        # 2. Apply accumulated trackball rotation
        rot_gl = self._rotation.T.astype(np.float32)
        glMultMatrixf(rot_gl)

        # ---- Wireframe mode ----------------------------------------
        if self._wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        # ---- Draw reference grid -----------------------------------
        self._draw_grid()

        # ---- Draw scene nodes --------------------------------------
        self.scene.render()

        glutSwapBuffers()

    # ------------------------------------------------------------------
    # Reference grid — helps orient the user in 3-D space
    # ------------------------------------------------------------------

    def _draw_grid(self) -> None:
        """
        Draw a flat XZ grid.  Lighting is disabled so the grid always
        appears the same shade regardless of scene lighting.
        """
        glDisable(GL_LIGHTING)
        glPushAttrib(GL_LINE_BIT)
        glLineWidth(1.0)
        glColor3f(0.30, 0.30, 0.34)

        HALF = 6
        STEP = 1
        glBegin(GL_LINES)
        for i in range(-HALF, HALF + 1, STEP):
            glVertex3f(float(i), -1.0, float(-HALF))
            glVertex3f(float(i), -1.0, float( HALF))
            glVertex3f(float(-HALF), -1.0, float(i))
            glVertex3f(float( HALF), -1.0, float(i))
        glEnd()

        glPopAttrib()
        glEnable(GL_LIGHTING)

    # ------------------------------------------------------------------
    # Picking — unproject mouse coords into a world-space ray
    # ------------------------------------------------------------------

    def _unproject_ray(self, mouse_x: int, mouse_y: int):
        """
        Convert a 2-D mouse position into a world-space ray using
        gluUnProject.

        gluUnProject reverses the full transform chain:
            screen → NDC → view → world

        We call it twice — once with z=0 (near plane) and once with z=1
        (far plane) — to get two world-space points, then form a direction.

        This ray is then passed to Scene.pick() for AABB intersection.
        """
        # OpenGL's y axis is bottom-up; screen y is top-down → flip
        gl_y = self.height - mouse_y

        near = np.array(gluUnProject(float(mouse_x), float(gl_y), 0.0))
        far  = np.array(gluUnProject(float(mouse_x), float(gl_y), 1.0))

        ray_dir = T.normalize(far - near)
        return near, ray_dir

    # ------------------------------------------------------------------
    # Event wiring — connect Interaction callbacks to Scene commands
    # ------------------------------------------------------------------

    def _connect_events(self) -> None:
        i = self.interaction

        i.register_callback('left_click',  self._on_left_click)
        i.register_callback('drag_left',   self._on_drag_left)   # rotate
        i.register_callback('drag_right',  self._on_drag_right)  # pan
        i.register_callback('scroll',      self._on_scroll)
        i.register_callback('key',         self._on_key)
        i.register_callback('move',        self._on_move)

    def _on_left_click(self, x: int, y: int) -> None:
        """Fire a pick ray; select the closest object."""
        origin, direction = self._unproject_ray(x, y)
        self.scene.pick(origin, direction)
        glutPostRedisplay()

    def _on_drag_left(self, dx: int, dy: int) -> None:
        """
        Trackball-style rotation.

        We decompose the 2-D mouse delta into two rotation components:
          - Horizontal drag (dx) → rotate around the scene's Y axis
          - Vertical drag   (dy) → rotate around the scene's X axis

        Accumulating these as matrix products avoids Euler gimbal lock.
        Each call rotates by a small angle proportional to mouse speed.
        """
        sensitivity = 0.3   # degrees per pixel
        ry = T.rotation_y(dx * sensitivity)
        rx = T.rotation_x(dy * sensitivity)
        # New rotation = new_rot × old_rot  (apply old first, then new)
        self._rotation = rx @ ry @ self._rotation
        glutPostRedisplay()

    def _on_drag_right(self, dx: int, dy: int) -> None:
        """Pan the view (translate the camera pivot point)."""
        self._pan_x += dx * 0.01
        self._pan_y -= dy * 0.01
        glutPostRedisplay()

    def _on_scroll(self, direction: int) -> None:
        """Zoom in (direction=+1) or out (direction=-1)."""
        self._camera_z += direction * self.ZOOM_STEP
        glutPostRedisplay()

    def _on_move(self, dx: float, dy: float, dz: float) -> None:
        """Arrow-key object translation."""
        self.scene.move_selected(dx, dy, dz)
        glutPostRedisplay()

    def _on_key(self, key: str, x: int, y: int) -> None:
        """
        Keyboard shortcuts:
            q / Esc — quit
            s       — scale up ×1.1
            S       — scale down ÷1.1
            c       — cycle selected object colour
            a       — add cube at origin
            A       — add sphere at origin
            d       — delete selected object
            w       — toggle wireframe mode
            r       — reset camera
            [       — move selected toward camera  (−Z)
            ]       — move selected away from camera (+Z)
        """
        STEP = 0.25
        if key in ('q', '\x1b'):   # q or Escape
            sys.exit(0)
        elif key == 's':
            self.scene.scale_selected(1.1)
        elif key == 'S':
            self.scene.scale_selected(1.0 / 1.1)
        elif key == 'c':
            self.scene.cycle_colour_selected()
        elif key == 'a':
            self.scene.add_cube()
        elif key == 'A':
            self.scene.add_sphere()
        elif key == 'd':
            self.scene.remove_selected()
        elif key == 'w':
            self._wireframe = not self._wireframe
        elif key == 'r':
            self._rotation  = T.identity()
            self._camera_z  = -7.0
            self._pan_x     = 0.0
            self._pan_y     = 0.0
        elif key == '[':
            self.scene.move_selected(0, 0, -STEP)   # toward camera
        elif key == ']':
            self.scene.move_selected(0, 0, +STEP)   # away from camera
        glutPostRedisplay()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Hand control to the GLUT event loop.  Does not return."""
        self._set_projection()
        glutMainLoop()
