import { useState } from 'react'

const Icon = ({ d, className = 'h-5 w-5' }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>
    <path d={d} />
  </svg>
)

const ICONS = {
  logo: 'M3 17.25l5.25-5.25 3.75 3.75L21 6.75m0 0h-5.25M21 6.75v5.25',
  deterministic: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  explainable: 'M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  review: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
  transfers: 'M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7 48.678 48.678 0 00-7.324 0 4.006 4.006 0 00-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3l-3-3m-11 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 003.7 3.7 48.656 48.656 0 007.324 0 4.006 4.006 0 003.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3l-3 3',
  correct: 'M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487z',
  export: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3',
  human: 'M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.997 0A17.9 17.9 0 0112 21.75c-2.676 0-5.216-.584-7.497-1.632',
  server: 'M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-2.268a3.375 3.375 0 00-2.4-1.014H15m.75 9l3.026 3.026a4.5 4.5 0 001.065-2.318M15.75 21H6.75A3.75 3.75 0 013 17.25V6.75A3.75 3.75 0 016.75 3h10.5A3.75 3.75 0 0121 6.75v3.75',
  upload: 'M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.875 4.875 0 01-1.857-9.442A5.25 5.25 0 019.75 8.25h.75m5 11.25h3.75a4.875 4.875 0 001.857-9.442A5.25 5.25 0 0015 8.25h-.75',
  lock: 'M16.5 10.5V7.5a4.5 4.5 0 10-9 0v3m-1.5 0h12a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5H6a1.5 1.5 0 01-1.5-1.5v-6A1.5 1.5 0 016 10.5z',
}

const NAV_LINKS = [
  { id: 'how-it-works', label: 'How it works' },
  { id: 'features', label: 'Features' },
  { id: 'security', label: 'Security' },
]

const TRUST_POINTS = [
  { label: 'Deterministic categorization', icon: ICONS.deterministic },
  { label: 'Explainable decisions', icon: ICONS.explainable },
  { label: 'Human-reviewed exceptions', icon: ICONS.human },
]

const STEPS = [
  {
    title: 'Upload your statement',
    body: 'Drop a CSV or JSON export from your bank or card. Common column names like Payee, Merchant, Debit/Credit, and Withdrawal/Deposit are recognized automatically.',
  },
  {
    title: 'Review & correct',
    body: 'Inspect the categorized transactions. Fix uncertain items with an inline dropdown; totals update as you go.',
  },
  {
    title: 'Export tax-ready results',
    body: 'Download a categorized CSV or JSON file with every decision explained — ready for your accountant (or next year’s you).',
  },
]

const FEATURES = [
  {
    title: 'Deterministic rule engine',
    body: 'Every category comes from an ordered, testable table of regex and keyword rules. Same input, same answer — every time.',
    icon: ICONS.deterministic,
    tone: 'wide',
    ruleIds: ['client_income', 'software', 'refund', 'transfers'],
  },
  {
    title: 'Explainable decisions',
    body: 'Each classified row names the rule that matched and says why, so your books are auditable line by line.',
    icon: ICONS.explainable,
    tone: 'tall',
  },
  {
    title: 'Uncertain-transaction detection',
    body: 'Opaque card noise and unknown merchants are flagged "Needs Review" instead of being guessed into a category.',
    icon: ICONS.review,
    tone: 'normal',
  },
  {
    title: 'Refund & transfer handling',
    body: 'Refunds are tracked apart from income and transfers between your own accounts never inflate expenses.',
    icon: ICONS.transfers,
    tone: 'normal',
  },
  {
    title: 'Review & correction workflow',
    body: 'Work the flagged queue with inline category selectors; corrections update totals instantly and are kept on export.',
    icon: ICONS.correct,
    tone: 'half',
  },
  {
    title: 'Categorized CSV & JSON export',
    body: 'Download tax-ready results with categories, statuses, and explanations — or re-upload an edited export seamlessly.',
    icon: ICONS.export,
    tone: 'half',
  },
]

const PREVIEW_ROWS = [
  { date: '2026-03-02', description: 'ACME DESIGN CLIENT PAYMENT INV 88', amount: '+$2,400.00', amountClass: 'text-emerald-600', category: 'Business Income', chipClass: 'bg-emerald-50 text-emerald-700', reason: "Matched rule 'client_income' for Business Income.", status: 'Reviewed' },
  { date: '2026-03-03', description: 'Adobe Creative Cloud', amount: '-$54.99', amountClass: 'text-ink-900', category: 'Software & Subscriptions', chipClass: 'bg-zinc-50 text-zinc-600', reason: "Matched rule 'software' for Software & Subscriptions.", status: 'Reviewed' },
  { date: '2026-03-05', description: 'Uber Trip Airport Transfer', amount: '-$38.20', amountClass: 'text-ink-900', category: 'Travel', chipClass: 'bg-zinc-50 text-zinc-600', reason: "Matched rule 'travel' for Travel.", status: 'Reviewed' },
  { date: '2026-03-06', description: 'GIMLET & CO., ANTIQUE MAP SHOP', amount: '-$145.00', amountClass: 'text-ink-900', category: 'Uncategorized', chipClass: 'bg-amber-50 text-amber-800', reason: 'No deterministic rule matched; flagged for human review instead of guessing.', status: 'Needs Review' },
  { date: '2026-03-11', description: 'Best Buy Refund', amount: '+$129.99', amountClass: 'text-zinc-500', category: 'Refund / Credit', chipClass: 'bg-zinc-50 text-zinc-600', reason: 'Positive amount matched the refund rule; recorded as a refund, not income.', status: 'Reviewed' },
  { date: '2026-03-18', description: 'Internal Transfer To Savings', amount: '-$600.00', amountClass: 'text-zinc-500', category: 'Transfers & Internal', chipClass: 'bg-zinc-100 text-zinc-500', reason: "Matched rule 'transfers'; moving your own money is neither income nor spending.", status: 'Reviewed' },
]

const SECURITY_POINTS = [
  ['Uploads go to your own backend only.', 'Your browser sends the file over HTTP to the StatementIQ server you run. There are no third-party analytics, storage, or AI services in the request path.'],
  ['Parsed in memory, never written to disk.', 'The server parses and categorizes the bytes inside its own process memory — no database, no file storage behind the request.'],
  ['Processed statements live in memory only.', 'Categorized results stay in the server process and disappear when the server restarts; nothing accumulates anywhere else.'],
  ['No LLMs, no external inference.', 'Categorization runs entirely in the local Python rule engine. Nothing about your transactions is ever sent to an AI provider.'],
  ['Export on your terms.', 'Results leave the app only when you click Export — as CSV or JSON saved directly by your browser.'],
]

function Logo({ dark = false }) {
  return (
    <a href="#top" className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
        <Icon d={ICONS.logo} className="h-4 w-4" />
      </span>
      <span className={`text-base font-bold tracking-tight ${dark ? 'text-white' : 'text-ink-900'}`}>StatementIQ</span>
    </a>
  )
}

function scrollToSection(event, id) {
  event.preventDefault()
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export default function Landing({ onCategorize, onTryDemo }) {
  const [menuOpen, setMenuOpen] = useState(false)

  function closeAnd(fn) {
    setMenuOpen(false)
    fn()
  }

  return (
    <div id="top" className="min-h-screen bg-[#fbfbfc]">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-ink-900/80 backdrop-blur-md">
        <nav aria-label="Primary" className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-6 py-3">
          <Logo dark />
          <div className="hidden items-center gap-7 text-sm font-medium text-zinc-300 md:flex">
            {NAV_LINKS.map((link) => (
              <a key={link.id} href={`#${link.id}`} onClick={(e) => scrollToSection(e, link.id)} className="transition hover:text-white">
                {link.label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onTryDemo} className="btn-ghost hidden text-zinc-300 hover:bg-white/10 hover:text-white md:inline-flex">
              Try demo
            </button>
            <button type="button" onClick={onCategorize} className="btn-primary whitespace-nowrap">
              Categorize<span className="hidden sm:inline"> statement</span>
            </button>
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="inline-flex items-center justify-center rounded-xl p-2.5 text-zinc-300 transition hover:bg-white/10 hover:text-white md:hidden"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                {menuOpen ? <path d="M18 6 6 18M6 6l12 12" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
              </svg>
            </button>
          </div>
        </nav>
        {menuOpen && (
          <div id="mobile-nav" className="border-t border-white/10 bg-ink-900/95 backdrop-blur-md md:hidden">
            <div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-3">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.id}
                  href={`#${link.id}`}
                  onClick={(e) => {
                    setMenuOpen(false)
                    scrollToSection(e, link.id)
                  }}
                  className="rounded-lg px-2 py-2.5 text-sm font-medium text-zinc-300 transition hover:bg-white/10 hover:text-white"
                >
                  {link.label}
                </a>
              ))}
              <button
                type="button"
                onClick={() => closeAnd(onTryDemo)}
                className="rounded-lg px-2 py-2.5 text-left text-sm font-medium text-zinc-300 transition hover:bg-white/10 hover:text-white"
              >
                Try demo
              </button>
            </div>
          </div>
        )}
      </header>

      <main>
        <section id="hero" aria-labelledby="hero-title" className="relative overflow-hidden bg-ink-900 pb-52 pt-24 sm:pb-64 sm:pt-28">
          <div aria-hidden="true" className="grid-pattern absolute inset-0" />
          <div aria-hidden="true" className="pointer-events-none absolute -top-32 left-1/2 h-[420px] w-[820px] max-w-full -translate-x-1/2 rounded-full bg-brand-600/25 blur-[130px]" />
          <div className="relative mx-auto max-w-6xl px-6 text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-2xs font-semibold tracking-wide text-zinc-300">
              <Icon d={ICONS.deterministic} className="h-3.5 w-3.5 text-brand-300" />
              Deterministic rule engine · No LLM-based categorization
            </span>
            <h1 id="hero-title" className="mx-auto mt-8 max-w-3xl text-balance text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
              Turn messy bank statements into{" "}
              <span className="whitespace-nowrap">tax-ready</span> transactions.
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-relaxed text-zinc-400 sm:text-lg">
              Upload your bank statement, automatically categorize transactions using transparent rules,
              review uncertain items, and export your results. No LLM-based categorization. No guessing.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <button type="button" onClick={onCategorize} className="btn-primary px-5 py-2.5">
                Categorize statement
              </button>
              <button
                type="button"
                onClick={onTryDemo}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur transition-all duration-150 ease-spring hover:bg-white/10 active:scale-[0.98]"
              >
                Explore demo
              </button>
            </div>
            <ul className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-zinc-400">
              {TRUST_POINTS.map((point) => (
                <li key={point.label} className="flex items-center gap-2">
                  <Icon d={point.icon} className="h-5 w-5 text-brand-300" />
                  {point.label}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="preview-title" className="relative z-10 -mt-40 pb-24 sm:-mt-48">
          <h2 id="preview-title" className="sr-only">Product preview</h2>
          <div className="mx-auto max-w-6xl px-6">
            <div className="panel shadow-float overflow-hidden">
              <div className="flex items-center gap-2 border-b border-black/[0.06] bg-zinc-50/80 px-4 py-3">
                <span aria-hidden="true" className="flex gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" />
                </span>
                <span className="mx-auto flex min-w-0 max-w-full items-center gap-1.5 rounded-full bg-white px-3 py-1 text-2xs text-zinc-500 ring-1 ring-black/[0.06]">
                  <Icon d={ICONS.lock} className="h-3 w-3 shrink-0 text-zinc-400" />
                  <span className="truncate">app.statementiq.local/dashboard</span>
                </span>
              </div>
              <div className="p-4 sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="label">demo-statement.csv · 20 transactions</p>
                  <span className="chip font-mono">engine v1 · deterministic</span>
                </div>
                <div className="mt-4 grid grid-cols-[repeat(2,minmax(0,1fr))] gap-3 lg:grid-cols-4">
                  {[
                    ['Income', '+$5,444.70', 'text-emerald-600', 'bg-white border-black/[0.06]'],
                    ['Expenses', '-$1,479.83', 'text-ink-900', 'bg-white border-black/[0.06]'],
                    ['Transfers', '$600.00', 'text-zinc-500', 'bg-white border-black/[0.06]'],
                    ['Needs review', '3', 'text-amber-700', 'bg-amber-50 border-amber-500/20'],
                  ].map(([label, value, valueClass, boxClass]) => (
                    <div key={label} className={`min-w-0 rounded-xl border p-4 ${boxClass}`}>
                      <p className="label truncate">{label}</p>
                      <p className={`num mt-1.5 truncate text-base font-bold sm:text-xl ${valueClass}`}>{value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 overflow-x-auto rounded-xl border border-black/[0.06]">
                  <table className="min-w-[640px] w-full divide-y divide-black/[0.05] text-left">
                    <thead className="bg-zinc-50/70">
                      <tr>
                        {['Date', 'Description', 'Amount', 'Category', 'Status'].map((h) => (
                          <th key={h} scope="col" className="label px-4 py-2.5">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-black/[0.05] bg-white">
                      {PREVIEW_ROWS.map((row) => (
                        <tr key={row.date} className={row.status === 'Needs Review' ? 'bg-amber-50/60' : ''}>
                          <td className="num whitespace-nowrap px-4 py-3 text-xs text-zinc-500">{row.date}</td>
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-ink-800">{row.description}</p>
                            <p className="mt-0.5 text-2xs text-zinc-500">{row.reason}</p>
                          </td>
                          <td className={`num whitespace-nowrap px-4 py-3 text-right text-sm font-semibold ${row.amountClass}`}>{row.amount}</td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className={`inline-flex items-center rounded-full border border-black/[0.06] px-2 py-0.5 text-2xs font-medium ${row.chipClass}`}>
                              {row.category}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-2xs font-semibold ring-1 ring-inset ${
                                row.status === 'Needs Review'
                                  ? 'bg-amber-100 text-amber-800 ring-amber-600/20'
                                  : 'bg-zinc-50 text-zinc-500 ring-black/[0.06]'
                              }`}
                            >
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <p className="mt-4 text-center text-2xs text-zinc-400">
              Illustrative data shown — all merchants, names and amounts are fictional.
            </p>
          </div>
        </section>

        <section id="how-it-works" aria-labelledby="how-title" className="scroll-mt-20 py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <p className="label">How it works</p>
              <h2 id="how-title" className="mx-auto mt-3 max-w-xl text-balance text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
                Three steps to a categorized ledger
              </h2>
            </div>
            <ol className="relative mt-16 grid gap-12 md:grid-cols-3 md:gap-8">
              <span aria-hidden="true" className="absolute left-[16%] right-[16%] top-6 hidden border-t border-black/[0.08] md:block" />
              {STEPS.map((step, index) => (
                <li key={step.title} className="relative">
                  <span className="num relative z-10 flex h-12 w-12 items-center justify-center rounded-full bg-white text-base font-bold text-brand-700 ring-1 ring-black/[0.08]">
                    {index + 1}
                  </span>
                  <h3 className="mt-5 text-base font-semibold text-ink-900">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-500">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="features" aria-labelledby="features-title" className="scroll-mt-20 border-t border-black/[0.05] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <p className="label">Features</p>
            <h2 id="features-title" className="mt-3 max-w-xl text-balance text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
              Built for trustworthy books
            </h2>
            <div className="mt-12 grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-2 lg:grid-cols-[repeat(6,minmax(0,1fr))]">
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  className={`card flex min-w-0 flex-col p-6 transition-all duration-200 ease-spring hover:-translate-y-0.5 hover:shadow-panel ${
                    feature.tone === 'wide' ? 'sm:col-span-2 lg:col-span-4'
                    : feature.tone === 'tall' ? 'lg:col-span-2 lg:row-span-2'
                    : feature.tone === 'half' ? 'lg:col-span-3'
                    : 'lg:col-span-2'
                  }`}
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <Icon d={feature.icon} />
                  </span>
                  <h3 className="mt-4 text-base font-semibold text-ink-900">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-500">{feature.body}</p>
                  {feature.ruleIds && (
                    <div className="mt-auto flex flex-wrap gap-2 pt-6">
                      {feature.ruleIds.map((rule) => (
                        <span key={rule} className="chip font-mono text-2xs">{rule}</span>
                      ))}
                    </div>
                  )}
                  {feature.tone === 'tall' && (
                    <dl className="mt-6 space-y-2 text-sm">
                      {[
                        ['Merchant text', 'ADOBE CREATIVE CLOUD FULL PLAN'],
                        ['Rule that fired', 'software'],
                        ['Category', 'Software & Subscriptions'],
                        ['Sign check', 'debit → expense'],
                      ].map(([term, value]) => (
                        <div key={term} className="flex items-baseline justify-between gap-4 border-b border-black/[0.05] pb-2">
                          <dt className="text-2xs uppercase tracking-label text-zinc-400">{term}</dt>
                          <dd className="num truncate font-mono text-xs text-ink-800">{value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {feature.tone === 'tall' && (
                    <div className="mt-6 rounded-xl bg-brand-50 p-4">
                      <p className="label text-brand-700">Why this row?</p>
                      <p className="mt-2 font-mono text-xs leading-relaxed text-brand-900">
                        Matched rule &#39;software&#39; for Software &amp; Subscriptions.
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="security" aria-labelledby="security-title" className="scroll-mt-20 border-t border-black/[0.05] py-24">
          <div className="mx-auto grid grid-cols-[minmax(0,1fr)] max-w-6xl gap-12 px-6 lg:grid-cols-2 lg:gap-16">
            <div className="min-w-0">
              <p className="label">Security &amp; privacy</p>
              <h2 id="security-title" className="mt-3 text-balance text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
                Your statement stays yours
              </h2>
              <p className="mt-4 leading-relaxed text-zinc-500">
                Here is exactly what happens to your data — no marketing hand-waving:
              </p>
              <ul className="mt-8 space-y-5">
                {SECURITY_POINTS.map(([title, body]) => (
                  <li key={title} className="flex gap-3">
                    <span className="mt-0.5 shrink-0 text-brand-600">
                      <Icon d={ICONS.deterministic} className="h-5 w-5" />
                    </span>
                    <p className="text-sm leading-relaxed text-zinc-600">
                      <span className="font-semibold text-ink-900">{title}</span> {body}
                    </p>
                  </li>
                ))}
              </ul>
              <p className="mt-8 rounded-xl border border-amber-500/15 bg-amber-50 p-4 text-sm leading-relaxed text-amber-800">
                Honest caveat: sessions live only in server memory — an unexported statement is lost when the
                server restarts, so download your results before shutting it down.
              </p>
            </div>
            <div className="min-w-0 self-start">
              <div className="relative overflow-hidden rounded-2xl bg-ink-900 p-6 shadow-float sm:p-8">
                <div aria-hidden="true" className="grid-pattern absolute inset-0" />
                <div className="relative">
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-mono text-xs text-zinc-400">GET /api/health</span>
                    <span className="font-mono text-2xs font-semibold text-emerald-300">200 OK</span>
                  </div>
                  <pre className="mt-5 overflow-x-auto font-mono text-xs leading-relaxed text-zinc-300">
{`{
  `}<span className="text-zinc-500">&quot;status&quot;</span>{`: `}<span className="text-emerald-300">&quot;ok&quot;</span>{`,
  `}<span className="text-zinc-500">&quot;engine&quot;</span>{`: `}<span className="text-emerald-300">&quot;deterministic-rule-engine-v1&quot;</span>{`,
  `}<span className="text-zinc-500">&quot;llm_used&quot;</span>{`: `}<span className="text-brand-300">false</span>{`
}`}
                  </pre>
                  <p className="mt-6 text-sm leading-relaxed text-zinc-400">
                    The API itself reports that no language model participates in categorization — the engine
                    is the same regex rule table that produced your categories.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section aria-labelledby="cta-title" className="border-t border-black/[0.05] py-28">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <h2 id="cta-title" className="text-balance text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
              Ready for a calmer tax season?
            </h2>
            <p className="mt-4 text-pretty leading-relaxed text-zinc-500">
              Upload a statement and see every transaction categorized — with reasons — in under a second.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <button type="button" onClick={onCategorize} className="btn-primary px-5 py-2.5">
                Categorize statement
              </button>
              <button type="button" onClick={onTryDemo} className="btn-secondary px-5 py-2.5">
                Explore demo
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-black/[0.05] bg-white py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-8 px-6 md:flex-row md:justify-between md:items-start">
          <Logo />
          <nav aria-label="Footer" className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-sm text-zinc-600">
            {NAV_LINKS.map((link) => (
              <a key={link.id} href={`#${link.id}`} onClick={(e) => scrollToSection(e, link.id)} className="py-2 transition hover:text-ink-900 md:py-0">
                {link.label}
              </a>
            ))}
          </nav>
          <p className="max-w-sm text-center text-2xs leading-relaxed text-zinc-500 md:text-right">
            deterministic regex rule engine · no external LLMs used for categorization · categorization is a
            bookkeeping aid, not tax advice
          </p>
        </div>
      </footer>
    </div>
  )
}
