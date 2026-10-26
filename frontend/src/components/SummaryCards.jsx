import { formatMoney } from '../lib/format'

function Cell({ label, value, hint, tone = 'ink', children }) {
  const toneClass = {
    ink: 'text-ink-900',
    negative: 'text-rose-600',
    positive: 'text-emerald-600',
    amber: 'text-amber-600',
  }[tone]
  return (
    <div className="px-4 py-4 sm:px-5">
      <p className="label">{label}</p>
      <p className={`mt-1.5 text-[18px] font-semibold leading-none tracking-tight num sm:text-[22px] ${toneClass}`}>
        {value}
      </p>
      {hint && <p className="mt-2 text-xs text-zinc-500">{hint}</p>}
      {children}
    </div>
  )
}

export default function SummaryCards({ summary, reviewFilterActive, onToggleReviewFilter }) {
  const flagged = summary.needs_review_count
  const grid =
    'grid grid-cols-[repeat(2,minmax(0,1fr))] gap-px overflow-hidden bg-black/[0.05] sm:grid-cols-3 xl:grid-cols-6'

  return (
    <section className={`panel ${grid}`} aria-label="Statement totals">
      <div className="bg-white">
        <Cell label="Transactions" value={summary.total_transactions} hint={summary.filename} />
      </div>
      <div className="bg-white">
        <Cell
          label="Expenses"
          value={formatMoney(summary.total_expenses)}
          tone="negative"
          hint="Excludes transfers"
        />
      </div>
      <div className="bg-white">
        <Cell
          label="Income"
          value={formatMoney(summary.total_income)}
          tone="positive"
          hint="Business income & interest"
        />
      </div>
      <div className="bg-white">
        <Cell
          label="Refunds"
          value={formatMoney(summary.total_refunds)}
          hint="Credits, not counted as income"
        />
      </div>
      <div className="bg-white">
        <Cell
          label="Net cash flow"
          value={formatMoney(summary.net_cash_flow)}
          tone={summary.net_cash_flow < 0 ? 'negative' : 'ink'}
          hint="Every transaction"
        />
      </div>
      <div className="bg-white">
        <button
          type="button"
          onClick={onToggleReviewFilter}
          aria-pressed={reviewFilterActive}
          className={`group flex h-full w-full flex-col items-start rounded-none px-4 py-4 text-left transition-colors sm:px-5 ${
            reviewFilterActive ? 'bg-amber-50' : 'hover:bg-amber-50/60'
          }`}
        >
          <span className="label flex items-center gap-1.5">
            Needs review
            {flagged > 0 && (
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500" aria-hidden="true">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            )}
          </span>
          <span className={`mt-1.5 text-[22px] font-semibold leading-none tracking-tight num ${flagged > 0 ? 'text-amber-600' : 'text-ink-900'}`}>
            {flagged}
          </span>
          <span className="mt-2 text-xs font-medium text-zinc-500 group-hover:text-amber-700">
            {reviewFilterActive ? 'Showing flagged only' : flagged > 0 ? 'Click to filter' : 'All reviewed'}
          </span>
        </button>
      </div>
    </section>
  )
}
