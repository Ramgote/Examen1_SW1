import { API_BASE as BASE } from './apiBase'

export async function api(path, { token, method = 'GET', body, sessionId } = {}) {
  const response = await fetch(`${BASE}/api/v1${path}`, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(sessionId ? { 'X-Collaboration-Session': sessionId } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (response.status === 204) return null
  const data = await response.json()
  if (!response.ok) {
    const detail = data.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => `${item.loc.filter(part => part !== 'body').join('.') || 'Diagrama'}: ${item.msg}`).join('\n')
      : detail?.message || 'Revisa los campos del formulario'
    const error = new Error(message)
    error.status = response.status
    error.detail = detail
    throw error
  }
  return data
}
