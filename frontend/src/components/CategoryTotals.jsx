import { formatMoney } from '../lib/format'

const INCOME = new Set(['Business Income', 'Interest Income'])

function tone(category) {
  if (category === 'Uncategorized') return { dot: 'bg-amber-400', bar: 'bg-amber-400/70' }
  if (category === 'Refund / Credit') return { dot: 'bg-sky-500', bar: 'bg-sky-500/70' }
  if (category === 'Transfers & Internal') return { dot: 'bg-zinc-400', bar: 'bg-zinc-400/60' }
  if (INCOME.has(category)) return { dot: 'bg-emerald-500', bar: 'bg-emerald-500/70' }
  return { dot: 'bg-brand-500', bar: 'bg-brand-500/70' }
}

export function ReviewProgress({ summary }) {
  const total = summary.total_transactions || 0
  const reviewed = summary.reviewed_count || 0
  const pct = total === 0 ? 0 : Math.round((reviewed / total) * 100)
  return (
    <div className="card px-5 py-4">
      <div className="flex items-baseline justify-between">
        <p className="label">Review progress</p>
        <p className="text-xs font-medium text-zinc-500 num">
          {reviewed} of {total} rows
        </p>
      </div>
      <div
        className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Transactions reviewed"
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-spring ${
            pct === 100 ? 'bg-emerald-500' : 'bg-brand-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-2.5 text-xs text-zinc-500">
        {summary.needs_review_count > 0
          ? `${summary.needs_review_count} row${summary.needs_review_count === 1 ? '' : 's'} still need a human decision.`
          : 'Every row has a category. Ready to export.'}
      </p>
    </div>
  )
}

export default function CategoryTotals({ summary, activeCategory, onSelectCategory }) {
  const entries = Object.values(summary.by_category || {})
    .filter((entry) => entry.count > 0)
    .sort((a, b) => Math.abs(b.total) - Math.abs(a.total) || a.category.localeCompare(b.category))
  const peak = Math.max(...entries.map((entry) => Math.abs(entry.total)), 1)

  return (
    <section className="card overflow-hidden" aria-label="Totals by category">
      <header className="flex items-center justify-between px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-ink-900">Totals by category</h2>
          <p className="mt-0.5 text-xs text-zinc-500">Select a category to filter the table</p>
        </div>
        <span className="chip">{entries.length}</span>
      </header>

      <ul className="max-h-[26rem] overflow-y-auto border-t border-black/[0.05]">
        {entries.map((entry) => {
          const colors = tone(entry.category)
          const isActive = activeCategory === entry.category
          const width = Math.max(3, (Math.abs(entry.total) / peak) * 100)
          return (
            <li key={entry.category}>
              <button
                type="button"
                onClick={() => onSelectCategory(entry.category)}
                aria-pressed={isActive}
                className={`flex w-full flex-col gap-1.5 px-5 py-3 text-left transition-colors hover:bg-zinc-50 ${
                  isActive ? 'bg-brand-50/70' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`h-2 w-2 shrink-0 rounded-full ${colors.dot}`} aria-hidden="true" />
                    <span className="truncate text-sm font-medium text-ink-800">{entry.category}</span>
                    <span className="shrink-0 text-xs text-zinc-400 num">×{entry.count}</span>
                  </span>
                  <span
                    className={`shrink-0 text-sm font-semibold num ${
                      entry.total < 0 ? 'text-ink-900' : 'text-emerald-600'
                    }`}
                  >
                    {formatMoney(entry.total)}
                  </span>
                </div>
                <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-100">
                  <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${width}%` }} />
                </div>
              </button>
            </li>
          )
        })}
      </ul>

      <footer className="border-t border-black/[0.05] bg-zinc-50/60 px-5 py-3 text-xs text-zinc-500">
        Expenses exclude transfers; refunds are reported separately and never as income.
      </footer>
    </section>
  )
}
