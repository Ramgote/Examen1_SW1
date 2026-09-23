import { serializeDiagram } from './document.js'
import { newId } from './id.js'

const equal = (a, b) => {
  if (a === b) return true
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false
  const keys = Object.keys(a)
  return keys.length === Object.keys(b).length && keys.every(key => Object.hasOwn(b, key) && equal(a[key], b[key]))
}

function mergeValue(base, draft, remote, path) {
  if (equal(draft, base)) return remote
  if (equal(remote, base) || equal(remote, draft)) return draft
  if ([base, draft, remote].every(v => v && typeof v === 'object' && !Array.isArray(v)) && !path.endsWith('/position')) {
    const result = Object.create(null)
    for (const key of new Set([...Object.keys(remote), ...Object.keys(draft), ...Object.keys(base)])) {
      const value = mergeValue(base[key], draft[key], remote[key], `${path}/${key}`)
      if (value !== undefined) result[key] = value
    }
    return result
  }
  throw new Error(`Conflicto en ${path}. Tu borrador se conserva: descárgalo antes de recargar el servidor.`)
}

export function mergeDocuments(base, draft, remote) {
  const result = { ...remote, metadata: mergeValue(base.metadata, draft.metadata, remote.metadata, 'metadata/position') }
  for (const field of ['nodes', 'edges']) {
    const maps = [base, draft, remote].map(doc => Object.fromEntries(doc[field].map(item => [item.id, item])))
    result[field] = Object.values(mergeValue(...maps, field))
  }
  return result
}

export function sameContent(a, b) {
  return !!a && !!b && equal(a.nodes, b.nodes) && equal(a.edges, b.edges) && equal(a.metadata, b.metadata)
}

// Framework-independent state machine: one update in flight, later edits stay local.
export class CollaborationClient {
  constructor({ url, token, role, notify, socketFactory = url => new WebSocket(url) }) {
    Object.assign(this, { url, token, role, notify, socketFactory })
    this.base = null; this.draft = null; this.latest = null; this.pending = null
    this.status = 'Conectando'; this.error = ''; this.participants = []
    this.ready = false; this.stopped = false; this.blocked = false; this.attempt = 0
    this.reservations = []; this.connectionId = null; this.requests = new Map()
  }

  emit() {
    this.notify({ diagram: this.draft, dirty: !!this.draft && !sameContent(this.base, this.draft),
      status: this.status, error: this.error, participants: this.participants, role: this.role,
      ready: this.ready, pending: !!this.pending, blocked: this.blocked,
      reservations: this.reservations, connectionId: this.connectionId })
  }

  start() { this.connect(); this.emit() }

  connect() {
    if (this.stopped) return
    const socket = this.socketFactory(this.url)
    this.socket = socket
    socket.onopen = () => {
      if (this.stopped) { socket.close(); return }
      socket.send(JSON.stringify({ type: 'authenticate', token: this.token }))
    }
    this.watchdog = setTimeout(() => socket.close(), 10000)
    socket.onmessage = event => {
      if (this.stopped || socket !== this.socket) return
      try { this.receive(JSON.parse(event.data)) }
      catch { this.error = 'Respuesta de colaboración inválida'; this.emit(); socket.close() }
    }
    socket.onerror = () => { /* onclose handles retry and keeps the draft. */ }
    socket.onclose = event => {
      if (this.stopped || socket !== this.socket) return
      clearTimeout(this.watchdog); clearInterval(this.heartbeat); clearTimeout(this.ackTimer)
      this.ready = false; this.pending = null; this.participants = []
      this.cancelRequests(); this.reservations = []; this.connectionId = null
      if ([4401, 4403, 1003, 1008, 1009].includes(event.code)) {
        this.status = 'Conexión cerrada'; this.role = 'VIEWER'; this.blocked = true
        this.error = event.code === 4401 ? 'Sesión vencida: descarga el borrador y vuelve a iniciar sesión.'
          : 'Acceso revocado o límite del canal alcanzado. Tu borrador se conserva.'
      } else {
        this.status = 'Sin conexión · borrador local'
        this.retry = setTimeout(() => this.connect(), Math.min(10000, 500 * 2 ** this.attempt++) + Math.random() * 300)
      }
      this.emit()
    }
  }

  receive(message) {
    if (message.type === 'pong') { this.lastPong = Date.now(); return }
    if (message.type === 'presence') {
      this.participants = message.participants; this.role = message.role
      this.reservations = message.reservations || []; this.connectionId = message.connection_id
      this.emit(); return
    }
    if (message.type === 'reservation_ack' || (message.type === 'error' && this.requests.has(message.op_id))) {
      const request = this.requests.get(message.op_id)
      if (request) {
        clearTimeout(request.timer); this.requests.delete(message.op_id)
        if (message.type === 'error') { this.error = message.message; request.resolve(false) }
        else { this.error = ''; request.resolve(true) }
      }
      this.emit(); return
    }
    if (message.type === 'error') {
      this.error = message.message
      if (!message.op_id || message.op_id === this.pending?.id) {
        this.pending = null; clearTimeout(this.ackTimer)
        this.blocked = true; this.conflict = message.code === 'conflict'
        if (message.code === 'forbidden') this.role = 'VIEWER'
      }
      this.emit(); return
    }
    if (message.type !== 'snapshot') return
    const remote = message.document
    this.role = message.role
    if (!this.latest || remote.version >= this.latest.version) this.latest = remote
    if (!this.ready) {
      clearTimeout(this.watchdog)
      this.ready = true; this.attempt = 0; this.status = 'En línea'; this.lastPong = Date.now()
      this.heartbeat = setInterval(() => {
        if (Date.now() - this.lastPong > 35000) this.socket.close()
        else this.socket.send(JSON.stringify({ type: 'ping' }))
      }, 10000)
    }
    if (this.pending && message.op_id !== this.pending.id) { this.emit(); return }
    if (this.base && remote.version < this.base.version) return
    const mergeBase = this.pending?.sent || this.base
    this.pending = null; clearTimeout(this.ackTimer)
    if (!this.blocked) {
      try {
        this.draft = this.draft ? mergeDocuments(mergeBase, this.draft, remote) : remote
        this.base = remote
        this.error = ''
      } catch (error) { this.error = error.message; this.blocked = true; this.conflict = true }
    }
    // A newer broadcast may have arrived before this acknowledgement.
    if (!this.blocked && this.latest.version > remote.version) {
      try { this.draft = mergeDocuments(this.base, this.draft, this.latest); this.base = this.latest }
      catch (error) { this.error = error.message; this.blocked = true; this.conflict = true }
    }
    this.emit(); this.schedule()
    if (this.finishRequested && !this.blocked && sameContent(this.base, this.draft)) {
      this.finishRequested = false; this.reservationRequest('release')
    }
  }

  reservationRequest(type, ids = []) {
    if (!this.ready || this.stopped || this.role === 'VIEWER') return Promise.resolve(false)
    if (type === 'reserve' && ids.every(id => this.reservations.some(r => r.node_id === id && r.connection_id === this.connectionId))) return Promise.resolve(true)
    const id = newId()
    return new Promise(resolve => {
      const timer = setTimeout(() => {
        this.requests.delete(id); this.error = 'No se pudo confirmar la reserva. Vuelve a intentarlo.'
        resolve(false); this.emit()
      }, 10000)
      this.requests.set(id, { resolve, timer })
      this.socket.send(JSON.stringify({ type, op_id: id, node_ids: ids }))
    })
  }

  finish() {
    if (!this.ready || this.blocked) return
    if (!this.pending && sameContent(this.base, this.draft)) this.reservationRequest('release')
    else { this.finishRequested = true; this.flush() }
  }

  cancelRequests() {
    for (const request of this.requests.values()) { clearTimeout(request.timer); request.resolve(false) }
    this.requests.clear()
  }

  edit(transform) {
    if (!this.draft || this.role === 'VIEWER') return
    const changed = serializeDiagram(transform(this.draft))
    if (sameContent(this.draft, changed)) return
    this.draft = changed
    if (!this.conflict) { this.blocked = false; this.error = '' }
    this.emit(); this.schedule()
  }

  schedule() {
    clearTimeout(this.debounce)
    this.debounce = setTimeout(() => this.flush(), 700)
  }

  flush() {
    clearTimeout(this.debounce)
    if (!this.ready || this.stopped || this.blocked || this.pending || this.role === 'VIEWER' || sameContent(this.base, this.draft)) return
    const sent = serializeDiagram({ ...this.draft, version: this.base.version })
    const id = newId()
    this.pending = { id, sent }
    this.socket.send(JSON.stringify({ type: 'update', op_id: id, base: this.base, document: sent }))
    this.ackTimer = setTimeout(() => this.socket.close(), 10000)
    this.emit()
  }

  reload() {
    if (!this.ready || !this.latest || this.pending) return
    this.draft = { ...this.latest }
    this.base = this.latest; this.blocked = false; this.conflict = false; this.error = ''
    this.emit()
    this.finishRequested = false; this.reservationRequest('release')
  }

  stop() {
    if (this.ready && this.socket?.readyState === 1) this.socket.send(JSON.stringify({ type: 'release', op_id: newId(), node_ids: [] }))
    this.stopped = true
    this.cancelRequests()
    for (const timer of [this.retry, this.debounce, this.watchdog, this.ackTimer]) clearTimeout(timer)
    clearInterval(this.heartbeat)
    this.socket?.close()
  }
}
