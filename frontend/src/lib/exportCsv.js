const EXPORT_COLUMNS = [
  'Date',
  'Description',
  'Amount',
  'Category',
  'Transaction Type',
  'Status',
  'Source',
  'Engine Rule',
  'Explanation',
  'Manual Override',
]

function escapeCsv(value) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function transactionRow(t) {
  return [
    t.date,
    escapeCsv(t.description),
    t.amount.toFixed(2),
    escapeCsv(t.category),
    t.transaction_type,
    t.status,
    t.source,
    escapeCsv(t.matched_rule ?? ''),
    escapeCsv(t.reason),
    t.manually_overridden ? 'yes' : 'no',
  ].join(',')
}

// Every line has exactly 10 fields so the export can be edited and
// re-uploaded without tripping CSV field-count validation.
export function buildTransactionsCsv(summary, transactions) {
  const lines = [EXPORT_COLUMNS.join(',')]
  for (const t of transactions) lines.push(transactionRow(t))
  return lines.join('\n')
}

export function buildTransactionsJson(summary, transactions) {
  return JSON.stringify(
    {
      schema: 'statementiq.export/v1',
      statement: {
        statement_id: summary.statement_id,
        filename: summary.filename,
        uploaded_at: summary.uploaded_at,
        summary,
      },
      transactions: transactions.map((t) => ({
        id: t.id,
        date: t.date,
        description: t.description,
        amount: t.amount,
        category: t.category,
        transaction_type: t.transaction_type,
        status: t.status,
        source: t.source,
        source_row: t.source_row,
        matched_rule: t.matched_rule,
        explanation: t.reason,
        original_category: t.original_category,
        manually_overridden: t.manually_overridden,
      })),
    },
    null,
    2,
  )
}

function saveFile(content, filename, mime) {
  // \uFEFF is written as an escape, not a literal: an invisible character in
  // the source was stripped once, and Excel needs the BOM for UTF-8 text.
  const blob = new Blob(['\uFEFF' + content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function downloadTransactionsCsv(summary, transactions) {
  const base = (summary.filename || 'statement').replace(/\.[^.]+$/, '')
  saveFile(buildTransactionsCsv(summary, transactions), `statementiq-${base}-export.csv`, 'text/csv')
}

export function downloadTransactionsJson(summary, transactions) {
  const base = (summary.filename || 'statement').replace(/\.[^.]+$/, '')
  saveFile(
    buildTransactionsJson(summary, transactions),
    `statementiq-${base}-export.json`,
    'application/json',
  )
}
