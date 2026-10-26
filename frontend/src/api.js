const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options)
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      /* keep generic message */
    }
    throw new Error(detail)
  }
  return response.json()
}

export function uploadStatement(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/statements', { method: 'POST', body: form })
}

export function getStatement(id) {
  return request(`/statements/${id}`)
}

export function overrideCategory(statementId, transactionId, category) {
  return request(`/statements/${statementId}/transactions/${transactionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
}

export function getCategories() {
  return request('/categories').then((body) => body.categories)
}
