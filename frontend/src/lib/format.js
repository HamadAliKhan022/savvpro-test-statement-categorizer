export function formatMoney(value) {
  const abs = Math.abs(value)
  const formatted = abs.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return `${value < 0 ? '-' : ''}$${formatted}`
}

export function formatDate(iso) {
  const [year, month, day] = iso.split('-')
  return `${month}/${day}/${year}`
}
