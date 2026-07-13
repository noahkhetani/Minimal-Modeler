import { useCallback, useEffect, useState } from 'react'
import type { ToastMsg } from './Toast'

interface Props {
  onToast: (message: string, kind?: ToastMsg['kind']) => void
}

export default function KeybindsPanel({ onToast }: Props): JSX.Element {
  const [keybinds, setKeybinds] = useState<Record<string, string>>({})
  const [labels, setLabels] = useState<[string, string][]>([])
  const [capturing, setCapturing] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      setLabels(await window.api.keybindLabels())
      setKeybinds(await window.api.getKeybinds())
    })()
  }, [])

  const labelOf = useCallback(
    (action: string) => labels.find(([a]) => a === action)?.[1] ?? action,
    [labels]
  )

  // grab the next keypress while rebinding
  useEffect(() => {
    if (!capturing) return
    const onKey = (e: KeyboardEvent): void => {
      e.preventDefault()
      const action = capturing
      setCapturing(null)
      if (e.key === 'Escape') {
        onToast('Rebind cancelled')
        return
      }
      const key = e.key
      if (key.length !== 1) {
        onToast('Please press a single character key', 'error')
        return
      }
      const clash = Object.entries(keybinds).find(([a, k]) => k === key && a !== action)
      if (clash) {
        onToast(`“${key}” is already bound to ${labelOf(clash[0])}`, 'error')
        return
      }
      const next = { ...keybinds, [action]: key }
      setKeybinds(next)
      void window.api.setKeybinds(next)
      onToast('Saved · applies next launch', 'success')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [capturing, keybinds, labelOf, onToast])

  const reset = useCallback(async () => {
    const fresh = await window.api.resetKeybinds()
    setKeybinds(fresh)
    onToast('Keybinds reset to defaults')
  }, [onToast])

  return (
    <div className="flex h-full flex-col p-7">
      <header className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Keybinds</h1>
          <p className="text-sm text-muted">
            Click a key to rebind, then press a new one. <span className="text-muted/70">Esc always quits.</span>
          </p>
        </div>
        <button
          onClick={() => void reset()}
          className="rounded-lg bg-panel-2 px-3.5 py-2 text-sm font-medium transition-colors hover:bg-border"
        >
          Reset to defaults
        </button>
      </header>

      <div className="flex-1 overflow-y-auto rounded-xl border border-border">
        {labels.map(([action], i) => (
          <div
            key={action}
            className={
              'flex items-center justify-between px-4 py-2.5 ' +
              (i !== 0 ? 'border-t border-border/60 ' : '')
            }
          >
            <span className="text-sm">{labelOf(action)}</span>
            <button
              onClick={() => setCapturing(action)}
              className={
                'min-w-[64px] rounded-md border px-3 py-1.5 text-center font-mono text-xs transition-colors ' +
                (capturing === action
                  ? 'animate-pulse border-ember bg-ember/15 text-ember'
                  : 'border-border bg-panel-2 text-ink hover:border-ember/60')
              }
            >
              {capturing === action ? 'press…' : displayKey(keybinds[action])}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function displayKey(key: string | undefined): string {
  if (!key) return '—'
  if (key === ' ') return 'Space'
  return key
}
