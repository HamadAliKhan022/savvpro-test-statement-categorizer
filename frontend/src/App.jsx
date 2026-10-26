import { useEffect, useMemo, useState } from 'react'
import Navbar from './components/Navbar'
import Landing from './components/Landing'
import FileDropzone from './components/FileDropzone'
import SummaryCards from './components/SummaryCards'
import CategoryTotals, { ReviewProgress } from './components/CategoryTotals'
import TransactionsTable from './components/TransactionsTable'
import ReviewToolbar from './components/ReviewToolbar'
import DetailsPanel from './components/DetailsPanel'
import { getCategories, overrideCategory, uploadStatement } from './api'
import { downloadTransactionsCsv, downloadTransactionsJson } from './lib/exportCsv'
import { DEMO_CSV } from './lib/demoData'

const PAGE_SIZE = 12

function WarningBanner({ warnings }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0" aria-hidden="true">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <div>
        <p className="font-semibold">Some rows were not imported</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-amber-700">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState('landing') // landing | upload | review
  const [categories, setCategories] = useState([])
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [savingId, setSavingId] = useState(null)

  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sort, setSort] = useState('date-asc')
  const [page, setPage] = useState(1)
  const [details, setDetails] = useState(null)

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  // ?demo=1 opens straight into the fictional statement, so the review
  // dashboard can be linked from the README or a walkthrough without an upload.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('demo') === '1') handleDemo()
  }, [])

  function resetFilters() {
    setOnlyNeedsReview(false)
    setSearch('')
    setCategoryFilter('')
    setStatusFilter('')
    setSort('date-asc')
    setPage(1)
  }

  async function processFile(file) {
    setBusy(true)
    setError('')
    try {
      const data = await uploadStatement(file)
      setResult(data)
      setView('review')
      resetFilters()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function handleDemo() {
    const file = new File([DEMO_CSV], 'demo-statement.csv', { type: 'text/csv' })
    setView('upload')
    processFile(file)
  }

  function downloadSample() {
    const blob = new Blob(['\uFEFF' + DEMO_CSV], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'statementiq-sample.csv'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  async function handleReassign(transaction, category) {
    if (category === transaction.category) return
    setSavingId(transaction.id)
    try {
      const data = await overrideCategory(result.summary.statement_id, transaction.id, category)
      setResult((prev) => ({
        ...prev,
        summary: data.summary,
        transactions: prev.transactions.map((row) =>
          row.id === transaction.id ? data.transaction : row,
        ),
      }))
      setDetails((prev) => (prev && prev.id === transaction.id ? data.transaction : prev))
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  const filtered = useMemo(() => {
    if (!result) return []
    let rows = result.transactions
    if (onlyNeedsReview) rows = rows.filter((t) => t.status === 'Needs Review')
    if (statusFilter) rows = rows.filter((t) => t.status === statusFilter)
    if (categoryFilter) rows = rows.filter((t) => t.category === categoryFilter)
    if (search.trim()) {
      const needle = search.trim().toLowerCase()
      rows = rows.filter((t) => t.description.toLowerCase().includes(needle))
    }
    const [key, direction] = sort.split('-')
    const factor = direction === 'asc' ? 1 : -1
    return [...rows].sort((a, b) =>
      key === 'date' ? a.date.localeCompare(b.date) * factor : (a.amount - b.amount) * factor,
    )
  }, [result, onlyNeedsReview, statusFilter, categoryFilter, search, sort])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount)
  const visible = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  if (view === 'landing') {
    return <Landing onCategorize={() => setView('upload')} onTryDemo={handleDemo} />
  }

  return (
    <div className="min-h-screen">
      <Navbar
        hasData={!!result}
        onHome={() => setView('landing')}
        onReset={() => {
          setResult(null)
          setView('upload')
          setError('')
        }}
        onExportCsv={() => downloadTransactionsCsv(result.summary, result.transactions)}
        onExportJson={() => downloadTransactionsJson(result.summary, result.transactions)}
      />

      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        {!result ? (
          <section className="mx-auto max-w-xl">
            <p className="label">Step 1 of 3 · Upload</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance text-ink-900 sm:text-4xl">
              Categorize statements, not guesses.
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed text-zinc-500">
              CSV or JSON. Columns are matched by name, so <span className="text-ink-800">Payee</span>,{' '}
              <span className="text-ink-800">Withdrawal / Deposit</span> and reordered or extra
              columns all work.
            </p>

            <div className="mt-7">
              <FileDropzone onFile={processFile} busy={busy} error={error} />
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
              <button type="button" onClick={handleDemo} disabled={busy} className="btn-primary">
                Try demo with fictional data
              </button>
              <button type="button" onClick={downloadSample} className="btn-secondary">
                Download sample CSV
              </button>
            </div>

            <div className="mt-6 flex items-start gap-2.5 rounded-xl bg-zinc-50 px-4 py-3 text-xs leading-relaxed text-zinc-500">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0" aria-hidden="true">
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>
                Your file is sent to your own StatementIQ backend and parsed in process memory —
                never written to disk, never forwarded to a third party, and no LLM decides a
                category. Sessions end when the server restarts.
              </span>
            </div>
          </section>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="label">Step 2 of 3 · Review</p>
                <h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-ink-900">
                  {result.summary.filename}
                </h1>
              </div>
              <div className="flex items-center gap-2">
                <span className="chip capitalize">
                  {result.summary.total_transactions} transactions
                </span>
                <button
                  type="button"
                  onClick={() => setOnlyNeedsReview((value) => !value)}
                  aria-pressed={onlyNeedsReview}
                  className={`btn ${
                    onlyNeedsReview
                      ? 'bg-amber-500 text-white hover:bg-amber-600'
                      : 'border border-black/[0.08] bg-white text-ink-800 hover:bg-zinc-50'
                  }`}
                >
                  Needs review
                  <span
                    className={`rounded-md px-1.5 py-0.5 text-xs num ${
                      onlyNeedsReview ? 'bg-amber-600' : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {result.summary.needs_review_count}
                  </span>
                </button>
              </div>
            </div>

            {result.warnings?.length > 0 && <WarningBanner warnings={result.warnings} />}

            <SummaryCards
              summary={result.summary}
              reviewFilterActive={onlyNeedsReview}
              onToggleReviewFilter={() => setOnlyNeedsReview((value) => !value)}
            />

            <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 xl:grid-cols-[minmax(0,1fr)_18rem]">
              <div className="min-w-0 space-y-4">
                <ReviewToolbar
                  search={search}
                  onSearch={(value) => {
                    setSearch(value)
                    setPage(1)
                  }}
                  category={categoryFilter}
                  onCategory={(value) => {
                    setCategoryFilter(value)
                    setPage(1)
                  }}
                  status={statusFilter}
                  onStatus={(value) => {
                    setStatusFilter(value)
                    setPage(1)
                  }}
                  sort={sort}
                  onSort={setSort}
                  categories={categories.filter((c) => c !== 'Uncategorized')}
                />

                <TransactionsTable
                  transactions={visible}
                  categories={categories}
                  onReassign={handleReassign}
                  savingId={savingId}
                  onOpenDetails={setDetails}
                  emptyMessage={
                    filtered.length === 0 && result.transactions.length > 0
                      ? 'No transactions match the current filters.'
                      : undefined
                  }
                />

                {pageCount > 1 && (
                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 text-sm text-zinc-500">
                    <span className="num">
                      Page {safePage} of {pageCount} · {filtered.length} rows
                    </span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={safePage === 1}
                        className="btn-secondary"
                      >
                        Previous
                      </button>
                      <button
                        type="button"
                        onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                        disabled={safePage === pageCount}
                        className="btn-secondary"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <aside className="min-w-0 space-y-4 xl:sticky xl:top-20">
                <ReviewProgress summary={result.summary} />
                <CategoryTotals
                  summary={result.summary}
                  activeCategory={categoryFilter}
                  onSelectCategory={(value) => {
                    setCategoryFilter((prev) => (prev === value ? '' : value))
                    setPage(1)
                  }}
                />
              </aside>
            </div>

            {error && (
              <div role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-5 pb-10 text-center text-xs text-zinc-400 sm:px-8">
        StatementIQ · deterministic regex rule engine · no external LLMs used for categorization ·
        categorization is a bookkeeping aid, not tax advice
      </footer>

      {details && (
        <DetailsPanel
          transaction={details}
          categories={categories}
          onReassign={handleReassign}
          onClose={() => setDetails(null)}
        />
      )}
    </div>
  )
}
