# minimal 3d modeller

a small 3d modeller i built to learn how cad/3d software actually works under the
hood. the modeller itself is python + pyopengl, and there's an electron + react +
tailwind start screen on top of it for managing projects and remapping keys.

## what it does

- **start screen** (electron/react/tailwind) - make/open/delete projects, edit keybinds, launch
- **projects** - each one is just a json scene file (empty, or with the demo objects)
- **keybinds** - rebind anything in the start screen, saved to keybinds.json
- scene graph using the composite pattern (cube, sphere, hierarchical node, snowman)
- trackball camera (matrix based, so no gimbal lock)
- ray picking (gluUnProject -> ray/aabb, closest hit wins)
- move / scale / colour-cycle / delete objects
- two-light shading, wireframe toggle
- undo/redo (z / Z) and save/load to json (o / l)

## install (windows)

grab the installer, no python or node needed:

**[latest release](https://github.com/noahkhetani/Minimal-Modeler/releases/latest)**

run it, click through the wizard (u get start menu + desktop shortcuts), done.
uninstall from add/remove programs. ur projects and keybinds live in
`%APPDATA%\Minimal3DModeller`.

## how the two pieces fit

the start screen and the modeller don't talk over a socket or anything - they just
share files in `%APPDATA%\Minimal3DModeller`. the start screen writes projects +
keybinds there, then spawns `Minimal3DModeller.exe --project <file>`, and the
modeller reads the same files. start screen owns the ui, modeller owns the 3d.

## running from source

just the modeller (python 3 + pyopengl + numpy):

```bash
pip install -r requirements.txt
python main.py                                # default scene
python main.py --project path/to/scene.json   # open a specific one
```

the start screen (electron dev, spawns the python modeller on launch):

```bash
cd desktop
pnpm install
pnpm dev
```

for the opengl/glut libs: on windows freeglut comes with the pyopengl wheels so
there's nothing to do. on ubuntu/debian `sudo apt-get install freeglut3-dev
libgl1-mesa-dev libglu1-mesa-dev`, on mac `brew install freeglut`.

## controls

mouse: left-click selects, left-drag rotates, right-drag pans, scroll zooms.

keys (these are the defaults, all rebindable in the start screen, esc always quits):

| key | does |
|---|---|
| `q` / `Esc` | quit |
| `a` / `A` | add cube / sphere |
| `s` / `S` | scale up / down |
| `c` | cycle colour |
| `d` | delete |
| `z` / `Z` | undo / redo |
| `o` / `l` | save / reload project |
| `w` | wireframe |
| `r` | reset camera |
| arrows | move object in x/y |
| `[` / `]` | move object toward / away from camera |

## layout

```
.
├── main.py            modeller entry, takes --project, loads keybinds
├── app.py             frozen-exe wrapper (stdout guard) for the modeller
├── viewer.py          window, gl setup, camera, render loop, undo/redo, save/load
├── scene.py           scene graph root, picking, manipulation, json serialisation
├── primitives.py      Node, Primitive, Cube, Sphere, HierarchicalNode, SnowFigure
├── interaction.py     glut input bus
├── transformations.py matrix math + ray/aabb test
├── config.py          keybinds (keybinds.json)
├── paths.py           where user data goes
├── tests/test_core.py headless tests
├── installer/build_modeller.py   freezes the modeller for the desktop app
├── desktop/           the electron + react + tailwind start screen
└── release/           built windows installer
```

## how a couple things work

**composite scene graph** - a Node is the base, Cube/Sphere are leaves, and a
HierarchicalNode holds child nodes. that's how the snowman is just three spheres
stacked in one node. to add a shape, subclass Primitive and fill in `_draw` and
`_local_aabb`.

**trackball** - rotation is stacked up as 4x4 matrix products, never euler angles,
so u can't hit gimbal lock.

**picking** - gluUnProject turns the click into a near/far world point, that gives
a ray, and we slab-test it against each node's box, nearest hit wins.

**serialisation** - `Scene.to_dict/from_dict` is one json layer that backs both
undo snapshots and save files, so an undo state and a saved project are literally
the same shape. the electron side writes the same format (desktop/src/main/data.ts).

## building the installer

```bash
pip install pyinstaller
python installer/build_modeller.py   # freeze modeller -> desktop/resources/modeller
cd desktop
pnpm install                         # ok's the electron/esbuild builds (pnpm-workspace.yaml)
pnpm dist                            # electron-builder -> release/...-Setup-1.0.0.exe
```

pyinstaller freezes the modeller, electron-builder bundles it in via extraResources
and spits out the nsis installer. the build turns off rcedit/signing
(`signAndEditExecutable: false`) so it doesn't drag in winCodeSign, which can't
unpack its mac symlinks on windows.

## tests

headless, no display needed:

```bash
python tests/test_core.py
```
