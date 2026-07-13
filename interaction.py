"""
the input system.

point of this is to keep input events (mouse, keyboard, scroll) away from the
rendering and scene stuff. the Interaction object is basically an event bus - it
hooks up the glut callbacks and fires named events at whoever registered for
them. classic observer / event-emitter thing.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Callable, Dict, List, Any

from OpenGL.GLUT import (
    glutMouseFunc, glutMotionFunc, glutPassiveMotionFunc,
    glutKeyboardFunc, glutSpecialFunc,
    GLUT_LEFT_BUTTON, GLUT_MIDDLE_BUTTON, GLUT_RIGHT_BUTTON,
    GLUT_DOWN, GLUT_UP,
    GLUT_KEY_UP, GLUT_KEY_DOWN, GLUT_KEY_LEFT, GLUT_KEY_RIGHT,
    GLUT_KEY_PAGE_UP, GLUT_KEY_PAGE_DOWN,
)


class Interaction:
    """
    central input handler.

    usage:
        interaction = Interaction()
        interaction.register_callback('left_click', my_handler)
    """

    # mouse buttons, exposed so nobody else touches raw glut constants
    LEFT   = GLUT_LEFT_BUTTON
    MIDDLE = GLUT_MIDDLE_BUTTON
    RIGHT  = GLUT_RIGHT_BUTTON

    # glut reports scroll as buttons 3/4
    SCROLL_UP   = 3
    SCROLL_DOWN = 4

    def __init__(self) -> None:
        # event_name -> [callable, ...]
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

        # mouse state so we can do drag deltas
        self.mouse_loc: tuple[int, int] = (0, 0)
        self.pressed: dict[int, bool] = {}

        self._register_glut_callbacks()

    def register_callback(self, event: str, fn: Callable) -> None:
        self._listeners[event].append(fn)

    def trigger(self, event: str, *args: Any, **kwargs: Any) -> None:
        # fire everyone listening for this event
        for fn in self._listeners[event]:
            fn(*args, **kwargs)

    def _register_glut_callbacks(self) -> None:
        glutMouseFunc(self._on_mouse_button)
        glutMotionFunc(self._on_mouse_drag)
        glutPassiveMotionFunc(self._on_mouse_move)
        glutKeyboardFunc(self._on_key)
        glutSpecialFunc(self._on_special_key)

    def _on_mouse_button(self, button: int, state: int, x: int, y: int) -> None:
        # turn raw button/state into named events so the rest of the app stays clean
        self.mouse_loc = (x, y)
        self.pressed[button] = (state == GLUT_DOWN)

        if state == GLUT_DOWN:
            if button == self.LEFT:
                self.trigger('left_click', x, y)
            elif button == self.RIGHT:
                self.trigger('right_click', x, y)
            elif button == self.SCROLL_UP:
                self.trigger('scroll', +1)       # zoom in
            elif button == self.SCROLL_DOWN:
                self.trigger('scroll', -1)       # zoom out

    def _on_mouse_drag(self, x: int, y: int) -> None:
        # fires while a button's held and the mouse moves - hand out a delta, not abs pos
        dx = x - self.mouse_loc[0]
        dy = y - self.mouse_loc[1]
        self.mouse_loc = (x, y)

        if self.pressed.get(self.LEFT):
            self.trigger('drag_left', dx, dy)
        elif self.pressed.get(self.RIGHT):
            self.trigger('drag_right', dx, dy)
        elif self.pressed.get(self.MIDDLE):
            self.trigger('drag_middle', dx, dy)

    def _on_mouse_move(self, x: int, y: int) -> None:
        # no button held, just track where the mouse is
        self.mouse_loc = (x, y)

    def _on_key(self, key: bytes, x: int, y: int) -> None:
        # stay dumb here - forward every key as one 'key' event, Viewer decides
        # what it means (see Viewer._on_key for the actual bindings)
        self.trigger('key', key.decode('utf-8', errors='replace'), x, y)

    def _on_special_key(self, key: int, x: int, y: int) -> None:
        # arrows move the selected object in x/y, pageup/down move it along z
        STEP = 0.25
        if   key == GLUT_KEY_LEFT:      self.trigger('move', -STEP,  0,      0)
        elif key == GLUT_KEY_RIGHT:     self.trigger('move', +STEP,  0,      0)
        elif key == GLUT_KEY_UP:        self.trigger('move',  0,    +STEP,   0)
        elif key == GLUT_KEY_DOWN:      self.trigger('move',  0,    -STEP,   0)
        elif key == GLUT_KEY_PAGE_UP:   self.trigger('move',  0,     0,    -STEP)
        elif key == GLUT_KEY_PAGE_DOWN: self.trigger('move',  0,     0,    +STEP)
