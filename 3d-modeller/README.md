# Minimal 3D Modeller

A compact, educational 3D modelling application built with Python, PyOpenGL, and NumPy.
Demonstrates the core architecture of professional CAD/3D software in ~800 lines of
clean, well-commented Python.

---

## Features

| System | Details |
|---|---|
| **Scene graph** | Composite pattern — Cube, Sphere, HierarchicalNode, SnowFigure |
| **Trackball camera** | Matrix-accumulated rotation — no gimbal lock |
| **Ray picking** | gluUnProject → ray-AABB intersection, closest-hit |
| **Object manipulation** | Translate (arrows), scale (s/S), colour-cycle (c), delete (d) |
| **Two-light Phong shading** | Key + fill, material shininess |
| **Reference grid** | XZ ground plane |
| **Wireframe mode** | Toggle with `w` |
| **Add primitives** | `a` for cube, `A` for sphere |
| **Event-driven input** | Decoupled Interaction bus → GLUT callbacks |

---

## File Layout

```
3d-modeller/
├── main.py              Entry point — creates Viewer and starts loop
├── viewer.py            Window, OpenGL init, camera, render loop
├── scene.py             Scene graph root, picking, manipulation commands
├── primitives.py        Node (ABC), Primitive, Cube, Sphere, HierarchicalNode, SnowFigure
├── interaction.py       GLUT event bus — decouples input from rendering
├── transformations.py   Matrix math, ray-AABB test, helpers
├── requirements.txt     Python dependencies
└── README.md            This file
```

---

## Setup & Installation

### 1. Install system OpenGL/GLUT libraries

**Ubuntu / Debian:**
```bash
sudo apt-get install freeglut3-dev libgl1-mesa-dev libglu1-mesa-dev
```

**macOS (Homebrew):**
```bash
brew install freeglut
```

**Windows:**
- Install freeglut from https://freeglut.sourceforge.net/
- Or use the version bundled with PyOpenGL_accelerate wheels

### 2. Install Python packages

```bash
pip install PyOpenGL PyOpenGL_accelerate numpy
```

Or from the requirements file:
```bash
pip install -r requirements.txt
```

### 3. Run

```bash
cd 3d-modeller
python main.py
```

---

## Controls

### Mouse
| Action | Effect |
|---|---|
| Left-click | Select object (ray picks closest AABB) |
| Left-drag | Rotate scene (trackball) |
| Right-drag | Pan camera |
| Scroll wheel | Zoom in / out |

### Keyboard
| Key | Action |
|---|---|
| `q` / `Esc` | Quit |
| `a` | Add cube at origin |
| `A` | Add sphere at origin |
| `s` | Scale selected up (×1.1) |
| `S` | Scale selected down (÷1.1) |
| `c` | Cycle colour of selected object |
| `d` | Delete selected object |
| `w` | Toggle wireframe |
| `r` | Reset camera |
| `← → ↑ ↓` | Move selected object (X/Y) |

---

## Architecture Notes

### Composite Pattern (scene graph)
```
Node (ABC)
├── Primitive (ABC)
│   ├── Cube
│   └── Sphere
└── HierarchicalNode
    └── SnowFigure  (children: bottom, torso, head spheres)
```
Adding a new shape: subclass `Primitive`, implement `_draw()` and `_local_aabb()`.

### Trackball Rotation
We accumulate rotation as 4×4 matrix products. Each drag delta produces a small
rotation matrix (around X or Y) that pre-multiplies the accumulated matrix. Because
we never extract Euler angles, gimbal lock cannot occur.

### Ray Picking
1. `gluUnProject` converts the mouse pixel into two world-space points (near/far plane).
2. The direction vector is `normalize(far − near)`.
3. For each scene node we run the slab-based ray-AABB test.
4. The node with the minimum positive `t` is selected.

### Transform Pipeline
```
Local space  →  (Node.model_matrix)  →  World space
World space  →  (camera transform)   →  View space
View space   →  (gluPerspective)     →  Clip / NDC / Screen space
```

---

## Extending the Modeller

| Idea | Where to start |
|---|---|
| Undo/redo | Save `(node, copy_of_matrices)` tuples to a stack before each mutation |
| Save/load | Serialise node type + matrices to JSON; rebuild on load |
| New primitives | Subclass `Primitive` — only `_draw` and `_local_aabb` needed |
| Mesh import | Add an `OBJMesh` node; render with `glDrawElements`; AABB from vertex data |
| Gizmo handles | Overlay arrow geometry in a separate render pass; pick handles first |
| Camera presets | Store/restore `_rotation`, `_camera_z`, `_pan_x`, `_pan_y` snapshots |
| Shader pipeline | Port draw calls to VAO/VBO + GLSL; keep the scene graph unchanged |
