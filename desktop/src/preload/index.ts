/**
 * safe bridge between the renderer and the main process. exposes a small typed
 * window.api and nothing else - no node access leaks into the ui.
 */
import { contextBridge, ipcRenderer } from 'electron'

const api = {
  listProjects: (): Promise<string[]> => ipcRenderer.invoke('projects:list'),
  createProject: (name: string, withDefaults: boolean): Promise<string> =>
    ipcRenderer.invoke('projects:create', name, withDefaults),
  deleteProject: (name: string): Promise<void> =>
    ipcRenderer.invoke('projects:delete', name),

  getKeybinds: (): Promise<Record<string, string>> => ipcRenderer.invoke('keybinds:get'),
  keybindLabels: (): Promise<[string, string][]> => ipcRenderer.invoke('keybinds:labels'),
  setKeybinds: (kb: Record<string, string>): Promise<void> =>
    ipcRenderer.invoke('keybinds:set', kb),
  resetKeybinds: (): Promise<Record<string, string>> => ipcRenderer.invoke('keybinds:reset'),

  launch: (name: string): Promise<boolean> => ipcRenderer.invoke('modeller:launch', name)
}

contextBridge.exposeInMainWorld('api', api)

export type Api = typeof api
