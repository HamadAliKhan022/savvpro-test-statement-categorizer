import { useEffect, useRef } from 'react'
import StatusBadge from './StatusBadge'
import { formatMoney, formatDate } from '../lib/format'

const SOURCE_COPY = {
  engine: 'Decided by the deterministic rule engine',
  imported: 'Category came from the uploaded file',
  manual: 'Set manually during review',
}

function Row({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <dt className="text-xs font-medium uppercase tracking-label text-zinc-500">{label}</dt>
      <dd className="text-right text-sm text-ink-800">{children}</dd>
    </div>
  )
}

export default function DetailsPanel({ transaction, categories, onReassign, onClose }) {
  const closeRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    function onKey(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-ink-900/25 backdrop-blur-[2px] animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-title"
        className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col bg-white shadow-float animate-slide-in"
      >
        <header className="flex items-center justify-between border-b border-black/[0.06] px-6 py-4">
          <div>
            <p className="label">{formatDate(transaction.date)}</p>
            <h2 id="details-title" className="mt-1 text-base font-semibold tracking-tight text-ink-900">
              Transaction details
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close transaction details"
            className="btn-ghost -mr-2 rounded-full p-2"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <p
            className={`text-3xl font-semibold tracking-tight num ${
              transaction.amount >= 0 ? 'text-emerald-600' : 'text-ink-900'
            }`}
          >
            {formatMoney(transaction.amount)}
          </p>
          <p className="mt-1.5 text-sm text-zinc-500">
            {transaction.description || 'No description on the statement line'}
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <StatusBadge status={transaction.status} />
            <span className="chip capitalize">{transaction.transaction_type}</span>
          </div>

          <section className="mt-6 rounded-xl bg-zinc-50 p-4">
            <p className="label">Why this category</p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-800">{transaction.reason}</p>
            {transaction.matched_rule && (
              <p className="mt-2 font-mono text-xs text-zinc-500">rule · {transaction.matched_rule}</p>
            )}
          </section>

          <dl className="mt-6 divide-y divide-black/[0.05]">
            <Row label="Source">{SOURCE_COPY[transaction.source] || transaction.source}</Row>
            {transaction.original_category && (
              <Row label="Engine said">{transaction.original_category}</Row>
            )}
            <Row label="Row in file">
              {transaction.source_row ? `#${transaction.source_row}` : '—'}
            </Row>
            <Row label="Transaction id">
              <span className="font-mono text-xs">{transaction.id}</span>
            </Row>
          </dl>

          <label className="mt-6 block">
            <span className="label">Category</span>
            <select
              value={transaction.category}
              onChange={(event) => onReassign(transaction, event.target.value)}
              className="field mt-1.5 cursor-pointer"
            >
              {[...new Set([transaction.category, ...categories])].map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>

          <p className="mt-4 text-xs leading-relaxed text-zinc-500">
            A category is a bookkeeping label, not a judgement about deductibility. Changing this
            row updates the totals and the export.
          </p>
        </div>
      </aside>
    </div>
  )
}
