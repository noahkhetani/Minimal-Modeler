import { useState } from 'react'

interface Props {
  onClose: () => void
  onCreated: (name: string) => void
  onError: (message: string) => void
}

export default function NewProjectModal({ onClose, onCreated, onError }: Props): JSX.Element {
  const [name, setName] = useState('')
  const [empty, setEmpty] = useState(true)
  const [busy, setBusy] = useState(false)

  const submit = async (): Promise<void> => {
    if (busy) return
    setBusy(true)
    try {
      const created = await window.api.createProject(name, !empty)
      onCreated(created)
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err))
      setBusy(false)
    }
  }

  return (
    <div
      className="absolute inset-0 z-20 grid place-items-center bg-black/50 backdrop-blur-sm"
      onMouseDown={onClose}
    >
      <div
        className="animate-rise w-[380px] rounded-2xl border border-border bg-panel p-6 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">New project</h2>
        <p className="mb-4 text-sm text-muted">Give it a name to get started.</p>

        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void submit()
            if (e.key === 'Escape') onClose()
          }}
          placeholder="e.g. my-scene"
          className="w-full rounded-lg border border-border bg-panel-2 px-3.5 py-2.5 text-sm outline-none placeholder:text-muted/60 focus:border-ember/70"
        />

        <label className="mt-4 flex cursor-pointer items-center gap-3 text-sm">
          <button
            type="button"
            role="switch"
            aria-checked={empty}
            onClick={() => setEmpty((v) => !v)}
            className={
              'relative h-6 w-11 rounded-full transition-colors ' +
              (empty ? 'bg-ember' : 'bg-border')
            }
          >
            <span
              className={
                'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ' +
                (empty ? 'left-[22px]' : 'left-0.5')
              }
            />
          </button>
          <span>
            Start empty
            <span className="block text-xs text-muted">Off = include the demo objects</span>
          </span>
        </label>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-muted transition-colors hover:bg-panel-2 hover:text-ink"
          >
            Cancel
          </button>
          <button
            onClick={() => void submit()}
            disabled={busy}
            className="rounded-lg bg-ember px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-ember-2 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  )
}
