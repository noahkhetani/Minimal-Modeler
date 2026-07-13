import { useCallback, useEffect, useState } from 'react'
import ProjectsPanel from './components/ProjectsPanel'
import KeybindsPanel from './components/KeybindsPanel'
import Toast, { type ToastMsg } from './components/Toast'

type Tab = 'projects' | 'keybinds'

function EmberMark(): JSX.Element {
  return (
    <div className="flex items-center gap-2.5">
      <span className="relative grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-ember to-ember-2 shadow-[0_0_18px_-2px_var(--color-ember)]">
        <span className="h-3.5 w-3.5 rounded-[3px] bg-white/90 rotate-45" />
      </span>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">Minimal 3D Modeller</div>
        <div className="text-[11px] text-muted">Start screen</div>
      </div>
    </div>
  )
}

function NavItem(props: {
  active: boolean
  label: string
  icon: JSX.Element
  onClick: () => void
}): JSX.Element {
  const { active, label, icon, onClick } = props
  return (
    <button
      onClick={onClick}
      className={
        'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ' +
        (active
          ? 'bg-panel-2 text-ink'
          : 'text-muted hover:bg-panel-2/60 hover:text-ink')
      }
    >
      <span className={active ? 'text-ember' : 'text-muted group-hover:text-ink'}>{icon}</span>
      {label}
    </button>
  )
}

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>('projects')
  const [toast, setToast] = useState<ToastMsg | null>(null)

  const notify = useCallback((message: string, kind: ToastMsg['kind'] = 'info') => {
    setToast({ message, kind, id: Math.random() })
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2600)
    return () => clearTimeout(t)
  }, [toast])

  return (
    <div className="flex h-full text-ink">
      {/* sidebar */}
      <aside className="flex w-60 flex-col border-r border-border bg-panel/70 px-3 py-4 backdrop-blur">
        <div className="px-2 pb-5">
          <EmberMark />
        </div>
        <nav className="flex flex-col gap-1">
          <NavItem
            active={tab === 'projects'}
            label="Projects"
            onClick={() => setTab('projects')}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              </svg>
            }
          />
          <NavItem
            active={tab === 'keybinds'}
            label="Keybinds"
            onClick={() => setTab('keybinds')}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="6" width="20" height="12" rx="2" />
                <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10" strokeLinecap="round" />
              </svg>
            }
          />
        </nav>
        <div className="mt-auto px-2 pt-4 text-[11px] text-muted">v1.0.0 · local-first</div>
      </aside>

      {/* content */}
      <main className="relative flex-1 overflow-hidden">
        <div key={tab} className="animate-rise h-full">
          {tab === 'projects' ? (
            <ProjectsPanel onToast={notify} />
          ) : (
            <KeybindsPanel onToast={notify} />
          )}
        </div>
        <Toast toast={toast} />
      </main>
    </div>
  )
}
