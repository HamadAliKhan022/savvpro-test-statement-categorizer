import { useCallback, useRef, useState } from 'react'

const ACCEPTED = ['.csv', '.json']
const MAX_BYTES = 10 * 1024 * 1024

function isAccepted(name) {
  const lower = name.toLowerCase()
  return ACCEPTED.some((ext) => lower.endsWith(ext))
}

function humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileDropzone({ onFile, busy, error }) {
  const [dragging, setDragging] = useState(false)
  const [localError, setLocalError] = useState(null)
  const [picked, setPicked] = useState(null)
  const inputRef = useRef(null)

  const handleFiles = useCallback(
    (files) => {
      const file = files?.[0]
      if (!file) return
      if (!isAccepted(file.name)) {
        setLocalError(
          `"${file.name}" is not a supported file type. Upload a .csv or .json statement.`,
        )
        setPicked(null)
        return
      }
      if (file.size > MAX_BYTES) {
        setLocalError(
          `"${file.name}" is ${humanSize(file.size)}. The limit is 10 MB — split the statement into smaller files.`,
        )
        setPicked(null)
        return
      }
      if (file.size === 0) {
        setLocalError('That file is empty. Please upload a statement with transaction rows.')
        setPicked(null)
        return
      }
      setLocalError(null)
      setPicked(file)
      onFile(file)
    },
    [onFile],
  )

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a CSV or JSON statement"
        onClick={() => !busy && inputRef.current?.click()}
        onKeyDown={(event) => {
          if ((event.key === 'Enter' || event.key === ' ') && !busy) {
            event.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          if (!busy) handleFiles(event.dataTransfer.files)
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-14 text-center transition-all duration-200 ease-spring ${
          dragging
            ? 'border-brand-500 bg-brand-50 shadow-glow'
            : 'border-zinc-300 bg-white hover:border-brand-400 hover:shadow-card'
        } ${busy ? 'pointer-events-none opacity-70' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />

        <div
          className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl transition-colors ${
            dragging ? 'bg-brand-600 text-white' : 'bg-brand-50 text-brand-600'
          }`}
        >
          {busy ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="animate-spin" aria-hidden="true">
              <path d="M21 12a9 9 0 1 1-6.2-8.6" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          )}
        </div>

        <p className="text-[15px] font-semibold tracking-tight text-ink-900">
          {busy ? 'Running the rule engine…' : 'Drop your statement here'}
        </p>
        <p className="mt-1 text-sm text-zinc-500">
          {busy ? (
            'Every row is matched against the deterministic rule table.'
          ) : (
            <>
              or <span className="font-semibold text-brand-600">browse</span> to choose a file
            </>
          )}
        </p>

        {picked && !localError && !busy && (
          <p className="chip mt-4 bg-white">
            {picked.name}
            <span className="text-zinc-400 num">{humanSize(picked.size)}</span>
          </p>
        )}
      </div>

      {(localError || error) && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2.5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="mt-0.5 shrink-0" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <span>{localError || error}</span>
        </div>
      )}
    </div>
  )
}
