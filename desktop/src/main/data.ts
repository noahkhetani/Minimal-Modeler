/**
 * project + keybind storage for the main process.
 *
 * everything sits under %APPDATA%\Minimal3DModeller - the same dir the python
 * modeller reads (see paths.py / config.py) - so projects made here open in the
 * modeller and keybinds edited here get picked up there.
 */
import { app } from 'electron'
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'fs'
import { join } from 'path'

export type Keybinds = Record<string, string>
export interface SceneDoc { nodes: unknown[] }

// action -> default key, mirrors config.DEFAULT_KEYBINDS
export const DEFAULT_KEYBINDS: Keybinds = {
  add_cube: 'a', add_sphere: 'A', scale_up: 's', scale_down: 'S',
  cycle_colour: 'c', delete: 'd', undo: 'z', redo: 'Z', save: 'o',
  load: 'l', wireframe: 'w', reset_camera: 'r', move_near: '[',
  move_far: ']', quit: 'q'
}

// (action, label) in order, mirrors config.ACTION_LABELS
export const ACTION_LABELS: [string, string][] = [
  ['add_cube', 'Add cube'], ['add_sphere', 'Add sphere'],
  ['scale_up', 'Scale selected up'], ['scale_down', 'Scale selected down'],
  ['cycle_colour', 'Cycle colour'], ['delete', 'Delete selected'],
  ['undo', 'Undo'], ['redo', 'Redo'], ['save', 'Save project'],
  ['load', 'Reload project'], ['wireframe', 'Toggle wireframe'],
  ['reset_camera', 'Reset camera'], ['move_near', 'Move toward camera'],
  ['move_far', 'Move away from camera'], ['quit', 'Quit']
]

function dataDir(): string {
  const dir = join(app.getPath('appData'), 'Minimal3DModeller')
  mkdirSync(dir, { recursive: true })
  return dir
}

function projectsDir(): string {
  const dir = join(dataDir(), 'projects')
  mkdirSync(dir, { recursive: true })
  return dir
}

function keybindsFile(): string {
  return join(dataDir(), 'keybinds.json')
}

export function sanitiseName(name: string): string {
  return name.replace(/[^A-Za-z0-9 _-]/g, '').trim()
}

export function projectPath(name: string): string {
  return join(projectsDir(), `${name}.json`)
}

export function listProjects(): string[] {
  return readdirSync(projectsDir())
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.slice(0, -5))
    .sort((a, b) => a.localeCompare(b))
}

function tmat(x: number, y: number, z: number): number[][] {
  return [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]
}
const IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

// the demo scene, same as Scene._build_default_scene (cube + sphere + snowman)
function defaultScene(): SceneDoc {
  return {
    nodes: [
      { kind: 'cube', translation: tmat(-1.5, 0, 0), scale: IDENTITY, colour_index: 1 },
      { kind: 'sphere', translation: tmat(1.5, 0, 0), scale: IDENTITY, colour_index: 2 },
      { kind: 'snowfigure', translation: tmat(0, -0.5, 0), scale: IDENTITY, colour_index: 0 }
    ]
  }
}

export function createProject(rawName: string, withDefaults: boolean): string {
  const name = sanitiseName(rawName)
  if (!name) throw new Error('Please enter a project name.')
  const path = projectPath(name)
  if (existsSync(path)) throw new Error(`A project named "${name}" already exists.`)
  const scene = withDefaults ? defaultScene() : { nodes: [] }
  writeFileSync(path, JSON.stringify(scene, null, 2), 'utf-8')
  return name
}

export function deleteProject(name: string): void {
  const path = projectPath(name)
  if (existsSync(path)) rmSync(path)
}

export function loadKeybinds(): Keybinds {
  const merged: Keybinds = { ...DEFAULT_KEYBINDS }
  try {
    const data = JSON.parse(readFileSync(keybindsFile(), 'utf-8'))
    for (const [action, key] of Object.entries(data)) {
      if (action in merged && typeof key === 'string' && key.length === 1) merged[action] = key
    }
  } catch {
    // missing or busted -> just use the defaults
  }
  return merged
}

export function saveKeybinds(kb: Keybinds): void {
  writeFileSync(keybindsFile(), JSON.stringify(kb, null, 2), 'utf-8')
}

export function resetKeybinds(): Keybinds {
  const fresh = { ...DEFAULT_KEYBINDS }
  saveKeybinds(fresh)
  return fresh
}
