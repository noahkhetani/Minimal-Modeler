import { useCallback, useEffect, useState } from 'react'
import NewProjectModal from './NewProjectModal'
import type { ToastMsg } from './Toast'

interface Props {
  onToast: (message: string, kind?: ToastMsg['kind']) => void
}

export default function ProjectsPanel({ onToast }: Props): JSX.Element {
  const [projects, setProjects] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const refresh = useCallback(
    async (select?: string) => {
      const list = await window.api.listProjects()
      setProjects(list)
      setSelected((prev) => select ?? (prev && list.includes(prev) ? prev : list[0] ?? null))
    },
    []
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  const launch = useCallback(
    async (name: string) => {
      await window.api.launch(name)
      onToast(`Launching “${name}”…`, 'success')
    },
    [onToast]
  )

  const remove = useCallback(async () => {
    if (!selected) return
    if (!confirm(`Delete project “${selected}”? This cannot be undone.`)) return
    await window.api.deleteProject(selected)
    onToast(`Deleted “${selected}”`)
    await refresh()
  }, [selected, onToast, refresh])

  return (
    <div className="flex h-full flex-col p-7">
      <header className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted">Open a scene, or start a new one.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-lg bg-panel-2 px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:bg-border"
        >
          + New project
        </button>
      </header>

      {projects.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-dashed border-border text-center">
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-xl bg-panel-2 text-ember">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
          </div>
          <p className="text-sm text-muted">No projects yet.</p>
          <button
            onClick={() => setModalOpen(true)}
            className="mt-3 rounded-lg bg-ember px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-ember-2"
          >
            Create your first project
          </button>
        </div>
      ) : (
        <div className="grid flex-1 auto-rows-min grid-cols-2 gap-3 overflow-y-auto pr-1 lg:grid-cols-3">
          {projects.map((name) => {
            const active = name === selected
            return (
              <button
                key={name}
                onClick={() => setSelected(name)}
                onDoubleClick={() => void launch(name)}
                className={
                  'group flex flex-col gap-3 rounded-xl border p-4 text-left transition-all ' +
                  (active
                    ? 'border-ember/60 bg-panel-2 shadow-[0_0_0_1px_var(--color-ember)]'
                    : 'border-border bg-panel hover:border-border/80 hover:bg-panel-2/60')
                }
              >
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-ember/25 to-ember-2/10 text-ember">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                    <path d="M3.3 7 12 12l8.7-5M12 22V12" />
                  </svg>
                </div>
                <div className="truncate text-sm font-medium">{name}</div>
              </button>
            )
          })}
        </div>
      )}

      <footer className="mt-5 flex items-center justify-between">
        <button
          onClick={() => void remove()}
          disabled={!selected}
          className="rounded-lg px-3.5 py-2 text-sm text-muted transition-colors hover:bg-red-500/15 hover:text-red-200 disabled:pointer-events-none disabled:opacity-40"
        >
          Delete
        </button>
        <button
          onClick={() => selected && void launch(selected)}
          disabled={!selected}
          className="rounded-lg bg-ember px-5 py-2.5 text-sm font-semibold text-white shadow-[0_6px_20px_-8px_var(--color-ember)] transition-colors hover:bg-ember-2 disabled:pointer-events-none disabled:opacity-40"
        >
          Launch ▶
        </button>
      </footer>

      {modalOpen && (
        <NewProjectModal
          onClose={() => setModalOpen(false)}
          onCreated={async (name) => {
            setModalOpen(false)
            await refresh(name)
            onToast(`Created “${name}”`, 'success')
          }}
          onError={(msg) => onToast(msg, 'error')}
        />
      )}
    </div>
  )
}
