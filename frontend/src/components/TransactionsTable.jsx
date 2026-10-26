import StatusBadge from './StatusBadge'
import { formatMoney, formatDate } from '../lib/format'

const SOURCE_LABELS = { imported: 'Imported', manual: 'Manual' }

function CategoryCell({ transaction, categories, onReassign, saving }) {
  const flagged = transaction.status === 'Needs Review'
  const editable = flagged || transaction.source !== 'engine'

  if (!editable) {
    return (
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate text-sm text-ink-800">{transaction.category}</span>
        {transaction.matched_rule && (
          <span
            title={`Engine rule: ${transaction.matched_rule}`}
            className="shrink-0 rounded-md bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500"
          >
            {transaction.matched_rule}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        aria-label={`Reassign category for ${transaction.description}`}
        disabled={saving}
        value={transaction.category}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => onReassign(transaction, event.target.value)}
        className={`w-full max-w-[13rem] cursor-pointer rounded-lg border px-2 py-1 text-sm font-medium transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50 ${
          flagged
            ? 'border-amber-300 bg-amber-50 text-amber-800'
            : 'border-black/[0.08] bg-white text-ink-800 hover:border-black/[0.16]'
        }`}
      >
        {[...new Set([transaction.category, ...categories])].map((category) => (
          <option key={category} value={category}>
            {category}
          </option>
        ))}
      </select>
      {SOURCE_LABELS[transaction.source] && (
        <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-700">
          {SOURCE_LABELS[transaction.source]}
        </span>
      )}
    </div>
  )
}

function TransactionCard({ transaction, categories, onReassign, saving, onOpenDetails }) {
  return (
    <li
      onClick={() => onOpenDetails(transaction)}
      className={`cursor-pointer px-4 py-3.5 transition-colors active:bg-zinc-50 ${
        transaction.status === 'Needs Review' ? 'bg-amber-50/40' : ''
      } ${saving ? 'opacity-60' : ''}`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <p className="num text-xs text-zinc-500">{formatDate(transaction.date)}</p>
        <p
          className={`num whitespace-nowrap text-sm font-semibold ${
            transaction.amount >= 0 ? 'text-emerald-600' : 'text-ink-900'
          }`}
        >
          {formatMoney(transaction.amount)}
        </p>
      </div>
      <p className="mt-1 break-words text-sm font-medium text-ink-900">
        {transaction.description || '— no description —'}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{transaction.reason}</p>
      <div className="mt-2.5" onClick={(event) => event.stopPropagation()}>
        <CategoryCell
          transaction={transaction}
          categories={categories}
          onReassign={onReassign}
          saving={saving}
        />
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-3">
        <StatusBadge status={transaction.status} />
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            onOpenDetails(transaction)
          }}
          aria-label={`Open details for ${transaction.description || 'this transaction'}`}
          className="rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-white hover:text-brand-600"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
        </button>
      </div>
    </li>
  )
}

export default function TransactionsTable({
  transactions,
  categories,
  onReassign,
  savingId,
  onOpenDetails,
  emptyMessage,
}) {
  return (
    <div className="panel overflow-hidden">
      {/* Six columns cannot fit a phone or a small tablet, so below lg the same rows
          re-render as cards. */}
      <ul className="divide-y divide-black/[0.05] lg:hidden">
        {transactions.map((transaction) => (
          <TransactionCard
            key={transaction.id}
            transaction={transaction}
            categories={categories}
            onReassign={onReassign}
            saving={savingId === transaction.id}
            onOpenDetails={onOpenDetails}
          />
        ))}
        {transactions.length === 0 && (
          <li className="px-4 py-14 text-center">
            <p className="text-sm font-medium text-zinc-500">
              {emptyMessage || 'Nothing here — every transaction has been categorized.'}
            </p>
          </li>
        )}
      </ul>

      <div className="hidden overflow-x-auto lg:block">
        {/* Fixed layout keeps the truncated description shrinkable; with auto layout its
            white-space:nowrap pinned the table at ~951px and forced sideways scrolling. */}
        <table className="w-full table-fixed text-left">
          <caption className="sr-only">Categorized transactions</caption>
          <thead className="sticky top-0 z-10 bg-zinc-50/90 backdrop-blur">
            <tr className="label">
              <th scope="col" className="w-[8rem] px-3 py-2.5 font-semibold">Date</th>
              <th scope="col" className="px-4 py-2.5 font-semibold">Description</th>
              <th scope="col" className="w-[7.5rem] px-4 py-2.5 text-right font-semibold">Amount</th>
              <th scope="col" className="w-[13rem] px-4 py-2.5 font-semibold">Category</th>
              <th scope="col" className="w-[8rem] px-4 py-2.5 font-semibold">Status</th>
              <th scope="col" className="w-[3rem] px-2 py-2.5">
                <span className="sr-only">Row actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-black/[0.05]">
            {transactions.map((transaction) => (
              <tr
                key={transaction.id}
                onClick={() => onOpenDetails(transaction)}
                className={`group cursor-pointer transition-colors hover:bg-zinc-50 ${
                  transaction.status === 'Needs Review' ? 'bg-amber-50/40' : ''
                } ${savingId === transaction.id ? 'opacity-60' : ''}`}
              >
                <td className="whitespace-nowrap px-3 py-3.5 text-sm text-zinc-500 num">
                  {formatDate(transaction.date)}
                </td>
                <td className="px-4 py-3.5">
                  <p className="truncate text-sm font-medium text-ink-900">
                    {transaction.description || '— no description —'}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-zinc-500">{transaction.reason}</p>
                </td>
                <td
                  className={`whitespace-nowrap px-4 py-3.5 text-right text-sm font-semibold num ${
                    transaction.amount >= 0 ? 'text-emerald-600' : 'text-ink-900'
                  }`}
                >
                  {formatMoney(transaction.amount)}
                </td>
                <td className="px-4 py-3.5" onClick={(event) => event.stopPropagation()}>
                  <CategoryCell
                    transaction={transaction}
                    categories={categories}
                    onReassign={onReassign}
                    saving={savingId === transaction.id}
                  />
                </td>
                <td className="whitespace-nowrap px-4 py-3.5">
                  <StatusBadge status={transaction.status} />
                </td>
                <td className="px-3 py-3.5 text-right">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      onOpenDetails(transaction)
                    }}
                    aria-label={`Open details for ${transaction.description || 'this transaction'}`}
                    className="rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-white hover:text-brand-600 group-hover:text-zinc-500"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 16v-4M12 8h.01" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
            {transactions.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-16 text-center">
                  <p className="text-sm font-medium text-zinc-500">
                    {emptyMessage || 'Nothing here — every transaction has been categorized.'}
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
