// A connection alone does not confirm that the current draft was saved.
export function saveStatus({ diagram, ready, pending, dirty, blocked, error, status }) {
  if (error || blocked) return { kind: 'error', label: dirty ? 'Error · cambios sin guardar' : 'Error de sincronización' }
  if (!ready) return { kind: 'offline', label: dirty ? 'Sin conexión · cambios sin guardar' : status || 'Conectando' }
  if (!diagram) return { kind: 'pending', label: 'Cargando diagrama…' }
  if (pending) return { kind: 'syncing', label: 'Sincronizando…' }
  if (dirty) return { kind: 'pending', label: 'Cambios pendientes' }
  return { kind: 'saved', label: `Guardado · v${diagram.version}` }
}

export function reloadDraft(shared, confirm) {
  if (!shared.ready || shared.pending || !shared.diagram) return false
  if (shared.dirty && !confirm('¿Descartar los cambios sin guardar y cargar la última versión recibida del servidor? Cancela y descarga el borrador primero si deseas conservarlo.')) return false
  shared.reload()
  return true
}
