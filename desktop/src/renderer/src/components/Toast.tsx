export interface ToastMsg {
  id: number
  message: string
  kind: 'info' | 'success' | 'error'
}

const STYLES: Record<ToastMsg['kind'], string> = {
  info: 'border-border bg-panel-2 text-ink',
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  error: 'border-red-500/40 bg-red-500/10 text-red-200'
}

export default function Toast({ toast }: { toast: ToastMsg | null }): JSX.Element | null {
  if (!toast) return null
  return (
    <div
      key={toast.id}
      className={
        'animate-rise pointer-events-none absolute bottom-5 left-1/2 -translate-x-1/2 rounded-lg border px-4 py-2 text-sm shadow-lg ' +
        STYLES[toast.kind]
      }
    >
      {toast.message}
    </div>
  )
}
