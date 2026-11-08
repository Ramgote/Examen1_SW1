// Local Vite keeps the local API; deployed builds use their own public origin.
const env = (typeof import.meta !== 'undefined' && import.meta.env) || {}
const hostname = (typeof window !== 'undefined' && window.location?.hostname) || 'localhost'
const origin = (typeof window !== 'undefined' && window.location?.origin) || 'http://localhost:8000'

export const API_BASE = (env.VITE_API_URL || (
  env.DEV ? `http://${hostname}:8000` : origin
)).replace(/\/$/, '')
