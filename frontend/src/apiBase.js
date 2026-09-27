// Local Vite keeps the local API; deployed builds use their own public origin.
export const API_BASE = (import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? `http://${window.location.hostname || 'localhost'}:8000` : window.location.origin
)).replace(/\/$/, '')
