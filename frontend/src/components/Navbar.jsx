function LogoMark() {
  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-ink-900 text-white shadow-[0_2px_8px_rgba(11,11,15,0.24)]">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4 19V7" />
        <path d="M10 19V4" />
        <path d="M16 19v-9" />
        <path d="M22 19H2" />
      </svg>
    </span>
  )
}

export default function Navbar({ onHome, onReset, onExportCsv, onExportJson, hasData }) {
  return (
    <header className="sticky top-0 z-30 border-b border-black/[0.06] bg-white/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-5 py-3 sm:px-8">
        <button type="button" onClick={onHome} className="group flex items-center gap-2.5 text-left">
          <LogoMark />
          <span className="text-[15px] font-semibold tracking-tight text-ink-900">
            StatementIQ
          </span>
        </button>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="chip mr-1 hidden bg-emerald-50 text-emerald-700 md:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Rule engine only · No LLMs
          </span>
          {hasData && (
            <>
              <button type="button" onClick={onExportCsv} className="btn-secondary">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="hidden sm:inline">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export CSV
              </button>
              <button type="button" onClick={onExportJson} className="btn-secondary" aria-label="Export this statement as JSON">
                JSON
              </button>
              <button type="button" onClick={onReset} className="btn-primary">
                New statement
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
