/**
 * electron main process for the start screen.
 *
 * makes the window, exposes project/keybind stuff to the renderer over ipc, and
 * spawns the python modeller as a detached process when u hit launch.
 */
import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { spawn } from 'child_process'
import { join } from 'path'
import * as data from './data'

function createWindow(): void {
  const win = new BrowserWindow({
    width: 960,
    height: 660,
    minWidth: 820,
    minHeight: 560,
    show: false,
    backgroundColor: '#0d0d12',
    title: 'Minimal 3D Modeller',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  win.once('ready-to-show', () => win.show())

  // open external links in the browser, never inside the app
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// cmd + args to open a project in the modeller (packaged vs dev)
function modellerCommand(projectPath: string): { cmd: string; args: string[] } {
  if (app.isPackaged) {
    // bundled pyinstaller exe under resources/modeller/
    const exe = join(process.resourcesPath, 'modeller', 'Minimal3DModeller.exe')
    return { cmd: exe, args: ['--project', projectPath] }
  }
  // dev: just run the python source (repo root is 3 up from desktop/out/main)
  const repoRoot = join(__dirname, '..', '..', '..')
  return { cmd: 'python', args: [join(repoRoot, 'main.py'), '--project', projectPath] }
}

function registerIpc(): void {
  ipcMain.handle('projects:list', () => data.listProjects())
  ipcMain.handle('projects:create', (_e, name: string, withDefaults: boolean) =>
    data.createProject(name, withDefaults))
  ipcMain.handle('projects:delete', (_e, name: string) => data.deleteProject(name))

  ipcMain.handle('keybinds:get', () => data.loadKeybinds())
  ipcMain.handle('keybinds:labels', () => data.ACTION_LABELS)
  ipcMain.handle('keybinds:set', (_e, kb: data.Keybinds) => data.saveKeybinds(kb))
  ipcMain.handle('keybinds:reset', () => data.resetKeybinds())

  ipcMain.handle('modeller:launch', (_e, name: string) => {
    const { cmd, args } = modellerCommand(data.projectPath(name))
    const child = spawn(cmd, args, { detached: true, stdio: 'ignore' })
    child.unref()
    return true
  })
}

app.whenReady().then(() => {
  registerIpc()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
