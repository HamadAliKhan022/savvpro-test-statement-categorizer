export default function StatusBadge({ status }) {
  const reviewed = status === 'Reviewed'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
        reviewed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${reviewed ? 'bg-emerald-500' : 'bg-amber-500'}`} />
      {reviewed ? 'Reviewed' : 'Needs review'}
    </span>
  )
}
