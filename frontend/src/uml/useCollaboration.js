import { useEffect, useRef, useState } from 'react'
import { CollaborationClient } from './collaboration'

export function useCollaboration(project, token) {
  const client = useRef(null)
  const [state, setState] = useState({ diagram: null, dirty: false, status: 'Conectando',
    error: '', participants: [], role: project.role, ready: false, pending: false, blocked: false })
  useEffect(() => {
    const url = new URL(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/projects/${project.id}/ws`)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    const connection = new CollaborationClient({ url: url.toString(), token, role: project.role, notify: setState })
    client.current = connection
    connection.start()
    return () => connection.stop()
  }, [project.id, project.role, token])
  return { ...state, change: transform => client.current?.edit(transform),
    reserve: ids => client.current?.reservationRequest('reserve', ids),
    finish: () => client.current?.finish(),
    acceptSaved: document => client.current?.receive({ type: 'snapshot', document, role: client.current.role, op_id: null }),
    save: () => client.current?.flush(), reload: () => client.current?.reload() }
}
