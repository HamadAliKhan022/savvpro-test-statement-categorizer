const STATUS_TABS = [
  { value: '', label: 'All' },
  { value: 'Reviewed', label: 'Reviewed' },
  { value: 'Needs Review', label: 'Needs review' },
]

const SORT_LABELS = {
  'date-asc': 'Oldest first',
  'date-desc': 'Newest first',
  'amount-asc': 'Smallest amount',
  'amount-desc': 'Largest amount',
}

export default function ReviewToolbar({
  search,
  onSearch,
  category,
  onCategory,
  status,
  onStatus,
  sort,
  onSort,
  categories,
}) {
  const filtersActive = Boolean(search || category || status) || sort !== 'date-asc'

  function clear() {
    onSearch('')
    onCategory('')
    onStatus('')
    onSort('date-asc')
  }

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <div className="relative min-w-[13rem] flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="search"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search description or merchant…"
          aria-label="Search transactions by description or merchant"
          className="field pl-9"
        />
      </div>

      <div
        className="flex items-center gap-0.5 rounded-xl border border-black/[0.06] bg-white p-0.5"
        role="group"
        aria-label="Filter by review status"
      >
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value || 'all'}
            type="button"
            onClick={() => onStatus(tab.value)}
            aria-pressed={status === tab.value}
            className={`rounded-[9px] px-2.5 py-1.5 text-xs font-semibold transition-colors ${
              status === tab.value
                ? 'bg-ink-900 text-white'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-ink-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <select
        aria-label="Filter by category"
        value={category}
        onChange={(event) => onCategory(event.target.value)}
        className="field w-auto cursor-pointer"
      >
        <option value="">All categories</option>
        {categories.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <select
        aria-label="Sort transactions"
        value={sort}
        onChange={(event) => onSort(event.target.value)}
        className="field w-auto cursor-pointer"
      >
        {Object.entries(SORT_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      {filtersActive && (
        <button type="button" onClick={clear} className="btn-ghost">
          Clear
        </button>
      )}
    </div>
  )
}
