"""
interaction.py — Event-driven interaction system.

Design goal: decouple input events (mouse, keyboard, scroll) from the
rendering and scene-graph logic.  The Interaction object acts as the
*event bus* — it registers GLUT callbacks and dispatches named events
to any number of listener callables registered by other subsystems.

This mirrors a classic Observer / Event-Emitter pattern.
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
    Centralised input handler.

    Usage:
        interaction = Interaction()
        interaction.register_callback('left_click', my_handler)

    Callback signatures vary by event; see each dispatch call below.
    """

    # Mouse button constants exposed for convenience
    LEFT   = GLUT_LEFT_BUTTON
    MIDDLE = GLUT_MIDDLE_BUTTON
    RIGHT  = GLUT_RIGHT_BUTTON

    # Scroll wheel pseudo-buttons (GLUT reports scroll as button 3/4)
    SCROLL_UP   = 3
    SCROLL_DOWN = 4

    def __init__(self) -> None:
        # listeners: event_name -> [callable, ...]
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

        # Track mouse state for drag detection
        self.mouse_loc: tuple[int, int] = (0, 0)
        self.pressed: dict[int, bool] = {}

        self._register_glut_callbacks()

    # ------------------------------------------------------------------
    # Public API — register / emit
    # ------------------------------------------------------------------

    def register_callback(self, event: str, fn: Callable) -> None:
        """Subscribe *fn* to *event*."""
        self._listeners[event].append(fn)

    def trigger(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Fire all listeners registered for *event*."""
        for fn in self._listeners[event]:
            fn(*args, **kwargs)

    # ------------------------------------------------------------------
    # GLUT callback registration
    # ------------------------------------------------------------------

    def _register_glut_callbacks(self) -> None:
        glutMouseFunc(self._on_mouse_button)
        glutMotionFunc(self._on_mouse_drag)
        glutPassiveMotionFunc(self._on_mouse_move)
        glutKeyboardFunc(self._on_key)
        glutSpecialFunc(self._on_special_key)

    # ------------------------------------------------------------------
    # Raw GLUT callbacks — translate to semantic events
    # ------------------------------------------------------------------

    def _on_mouse_button(self, button: int, state: int, x: int, y: int) -> None:
        """
        GLUT calls this on any mouse button press/release.
        We translate button/state combos into semantic event names so the
        rest of the app never has to compare raw GLUT constants.
        """
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
        """
        Called while any button is held and mouse moves.
        Compute delta from last known position so listeners get a *delta*,
        not an absolute screen position.
        """
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
        """Passive move (no button held) — update position only."""
        self.mouse_loc = (x, y)

    def _on_key(self, key: bytes, x: int, y: int) -> None:
        """
        ASCII keyboard input.

        Keys:
            q / Esc — quit
            s       — scale up
            S       — scale down
            c       — cycle colour
            a       — add cube
            A       — add sphere
            z       — undo
            w       — toggle wireframe
            d       — delete selected
        """
        self.trigger('key', key.decode('utf-8', errors='replace'), x, y)

    def _on_special_key(self, key: int, x: int, y: int) -> None:
        """
        Arrow keys → translate selected object in X/Y.
        Page Up / Page Down → translate along Z axis (toward / away from camera).
        """
        STEP = 0.25
        if   key == GLUT_KEY_LEFT:      self.trigger('move', -STEP,  0,      0)
        elif key == GLUT_KEY_RIGHT:     self.trigger('move', +STEP,  0,      0)
        elif key == GLUT_KEY_UP:        self.trigger('move',  0,    +STEP,   0)
        elif key == GLUT_KEY_DOWN:      self.trigger('move',  0,    -STEP,   0)
        elif key == GLUT_KEY_PAGE_UP:   self.trigger('move',  0,     0,    -STEP)
        elif key == GLUT_KEY_PAGE_DOWN: self.trigger('move',  0,     0,    +STEP)
