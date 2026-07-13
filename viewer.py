"""
window, opengl setup, camera and the render loop.

the Viewer sits between the os/gl driver and our scene. it makes the glut
window, sets the projection, does the camera transform, clears + kicks off
render passes, and wires the input bus to scene commands.

spaces go: local -> (per-node model matrix) -> world -> (camera) -> view ->
(gluPerspective) -> clip/ndc/screen. the "camera" is really just the inverse of
a world transform - we never move a camera, we move the world, same thing.

trackball: dragging horizontally spins around y, vertically around x. we stack
the rotations as matrix products instead of euler angles so u never hit gimbal
lock (that's when two axes line up and u lose a degree of freedom).
"""

from __future__ import annotations
import sys
import numpy as np

from OpenGL.GL import (
    glClear, glClearColor, glEnable, glDisable,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LIGHTING, GL_LIGHT0, GL_LIGHT1,
    GL_NORMALIZE,
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
    """owns the gl window and drives rendering. width/height/title are obvious."""

    # perspective projection settings
    FOV = 45.0
    NEAR_CLIP = 0.1
    FAR_CLIP  = 1000.0

    # how far the scroll wheel moves the camera along z per tick
    ZOOM_STEP = 0.5

    # file used by save (o) / load (l) when no project is open
    SCENE_FILE = "scene.json"

    def __init__(self, width: int = 900, height: int = 600, title: str = "3D Modeller",
                 keybinds: dict | None = None, project_path: str | None = None) -> None:
        self.width  = width
        self.height = height

        # action -> key keybinds. default so the modeller runs on its own without
        # the start screen. index by key for fast lookup per keystroke.
        from config import DEFAULT_KEYBINDS
        self._keybinds: dict = dict(keybinds) if keybinds else dict(DEFAULT_KEYBINDS)
        self._action_by_key: dict = {k: a for a, k in self._keybinds.items()}

        # project file behind save/load. None -> the generic SCENE_FILE
        self._project_path: str | None = project_path

        # trackball rotation, stacked as 4x4 matrices (no euler = no gimbal)
        self._rotation: np.ndarray = T.identity()

        # zoom (camera z distance)
        self._camera_z: float = -7.0

        # pan (right-drag)
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0

        self._wireframe: bool = False

        # undo/redo - each entry is a full scene snapshot. we snapshot before
        # any mutation; redo fills up as u undo and clears on a fresh change.
        self._undo_stack: list = []
        self._redo_stack: list = []

        self._init_glut(title)
        self._init_gl()

        self.scene       = Scene()
        self.interaction = Interaction()

        # if a project was passed, load it over the default scene (empty = clear)
        if self._project_path and not self.scene.load_from_file(self._project_path):
            print(f"[project] '{self._project_path}' not found - starting from the default scene")

        self._connect_events()

    def _init_glut(self, title: str) -> None:
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
        glutInitWindowSize(self.width, self.height)
        glutCreateWindow(title.encode())

        glutDisplayFunc(self._render)
        glutReshapeFunc(self._reshape)

    def _init_gl(self) -> None:
        # one-time fixed-function gl state
        glClearColor(0.15, 0.15, 0.18, 1.0)   # dark bg
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)                 # renormalise normals after scaling
        glEnable(GL_LIGHTING)

        # key light + soft fill
        self._setup_lights()

    def _setup_lights(self) -> None:
        # LIGHT0 = key from upper-left, LIGHT1 = fill from the right.
        # position w=1 is positional, w=0 is directional.
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 8.0, 5.0, 0.0])    # directional
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.97, 0.90, 1.0])  # warm white
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.15, 0.15, 0.18, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.6, 0.6, 0.6, 1.0])

        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_POSITION, [-5.0, 3.0, -3.0, 0.0])  # fill, other side
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.25, 0.30, 0.40, 1.0]) # cool blue
        glLightfv(GL_LIGHT1, GL_AMBIENT,  [0.0,  0.0,  0.0,  1.0])
        glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0,  0.0,  0.0,  1.0])

    def _reshape(self, width: int, height: int) -> None:
        self.width  = width
        self.height = max(height, 1)  # no divide-by-zero
        glViewport(0, 0, self.width, self.height)
        self._set_projection()

    def _set_projection(self) -> None:
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width / self.height
        gluPerspective(self.FOV, aspect, self.NEAR_CLIP, self.FAR_CLIP)
        glMatrixMode(GL_MODELVIEW)

    def _render(self) -> None:
        # glut calls this every frame
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # camera transform (moves the world, not the camera): pull back on z...
        from OpenGL.GL import glTranslatef
        glTranslatef(self._pan_x, self._pan_y, self._camera_z)

        # ...then apply the trackball rotation
        rot_gl = self._rotation.T.astype(np.float32)
        glMultMatrixf(rot_gl)

        if self._wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        self._draw_grid()
        self.scene.render()

        glutSwapBuffers()

    def _draw_grid(self) -> None:
        # flat xz grid. lighting off so it's a constant shade
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

    def _unproject_ray(self, mouse_x: int, mouse_y: int):
        # turn a 2d mouse pos into a world-space ray with gluUnProject, which
        # runs the transform chain backwards (screen -> ndc -> view -> world).
        # do it at z=0 (near) and z=1 (far), the direction is far - near.
        # gl's y is bottom-up, screen y is top-down, so flip it
        gl_y = self.height - mouse_y

        near = np.array(gluUnProject(float(mouse_x), float(gl_y), 0.0))
        far  = np.array(gluUnProject(float(mouse_x), float(gl_y), 1.0))

        ray_dir = T.normalize(far - near)
        return near, ray_dir

    def _connect_events(self) -> None:
        i = self.interaction

        i.register_callback('left_click',  self._on_left_click)
        i.register_callback('drag_left',   self._on_drag_left)   # rotate
        i.register_callback('drag_right',  self._on_drag_right)  # pan
        i.register_callback('scroll',      self._on_scroll)
        i.register_callback('key',         self._on_key)
        i.register_callback('move',        self._on_move)

    def _on_left_click(self, x: int, y: int) -> None:
        # cast a pick ray, select whatever's closest
        origin, direction = self._unproject_ray(x, y)
        self.scene.pick(origin, direction)
        glutPostRedisplay()

    def _on_drag_left(self, dx: int, dy: int) -> None:
        # trackball rotate: horizontal drag -> y axis, vertical -> x axis.
        # stacking as matrix products dodges euler gimbal lock.
        sensitivity = 0.3   # degrees per pixel
        ry = T.rotation_y(dx * sensitivity)
        rx = T.rotation_x(dy * sensitivity)
        # new = new x old (old applied first)
        self._rotation = rx @ ry @ self._rotation
        glutPostRedisplay()

    def _on_drag_right(self, dx: int, dy: int) -> None:
        # pan the view
        self._pan_x += dx * 0.01
        self._pan_y -= dy * 0.01
        glutPostRedisplay()

    def _on_scroll(self, direction: int) -> None:
        # +1 zoom in, -1 zoom out
        self._camera_z += direction * self.ZOOM_STEP
        glutPostRedisplay()

    # undo/redo, snapshot based (see Scene.to_dict / from_dict)

    def _snapshot(self) -> None:
        # save the current scene so the next mutation can be undone
        self._undo_stack.append(self.scene.to_dict())
        self._redo_stack.clear()

    def _undo(self) -> None:
        if not self._undo_stack:
            print("[undo] nothing to undo")
            return
        self._redo_stack.append(self.scene.to_dict())
        self.scene.from_dict(self._undo_stack.pop())

    def _redo(self) -> None:
        if not self._redo_stack:
            print("[redo] nothing to redo")
            return
        self._undo_stack.append(self.scene.to_dict())
        self.scene.from_dict(self._redo_stack.pop())

    # save/load json scene files, same serialisation layer

    def _target_file(self) -> str:
        # what save/load hit - the open project, or SCENE_FILE if none
        return self._project_path or self.SCENE_FILE

    def _save_scene(self) -> None:
        target = self._target_file()
        self.scene.save_to_file(target)
        print(f"[save] scene written to {target}")

    def _load_scene(self) -> None:
        target = self._target_file()
        self._snapshot()  # so a load can be undone too
        if self.scene.load_from_file(target):
            print(f"[load] scene restored from {target}")
        else:
            self._undo_stack.pop()  # nothing changed, drop the snapshot
            print(f"[load] could not read {target}")

    def _on_move(self, dx: float, dy: float, dz: float) -> None:
        # arrow-key move, only if something's selected
        if self.scene.selected is None:
            return
        self._snapshot()
        self.scene.move_selected(dx, dy, dz)
        glutPostRedisplay()

    def _on_key(self, key: str, x: int, y: int) -> None:
        # map the pressed char to an action (see config.py) then run it.
        # mutating actions snapshot first; camera stuff (wireframe/reset/zoom/
        # rotate/pan) isn't undoable. esc always quits no matter the bindings.
        STEP = 0.25
        if key == '\x1b':          # esc, unbindable quit
            sys.exit(0)

        action = self._action_by_key.get(key)
        if action is None:
            return

        if action == 'quit':
            sys.exit(0)
        elif action == 'add_cube':
            self._snapshot()
            self.scene.add_cube()
        elif action == 'add_sphere':
            self._snapshot()
            self.scene.add_sphere()
        elif action == 'scale_up':
            if self.scene.selected:
                self._snapshot()
                self.scene.scale_selected(1.1)
        elif action == 'scale_down':
            if self.scene.selected:
                self._snapshot()
                self.scene.scale_selected(1.0 / 1.1)
        elif action == 'cycle_colour':
            if self.scene.selected:
                self._snapshot()
                self.scene.cycle_colour_selected()
        elif action == 'delete':
            if self.scene.selected:
                self._snapshot()
                self.scene.remove_selected()
        elif action == 'undo':
            self._undo()
        elif action == 'redo':
            self._redo()
        elif action == 'save':
            self._save_scene()
        elif action == 'load':
            self._load_scene()
        elif action == 'wireframe':
            self._wireframe = not self._wireframe
        elif action == 'reset_camera':
            self._rotation  = T.identity()
            self._camera_z  = -7.0
            self._pan_x     = 0.0
            self._pan_y     = 0.0
        elif action == 'move_near':
            if self.scene.selected:
                self._snapshot()
                self.scene.move_selected(0, 0, -STEP)   # toward camera
        elif action == 'move_far':
            if self.scene.selected:
                self._snapshot()
                self.scene.move_selected(0, 0, +STEP)   # away from camera
        glutPostRedisplay()

    def run(self) -> None:
        # hand off to glut's loop, never returns
        self._set_projection()
        glutMainLoop()
