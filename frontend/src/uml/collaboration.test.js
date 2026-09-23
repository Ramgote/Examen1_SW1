import test from 'node:test'
import assert from 'node:assert/strict'
import { CollaborationClient, mergeDocuments } from './collaboration.js'
import { saveStatus } from './saveStatus.js'

const diagram = () => ({ schema_version: 1, version: 1, nodes: [{ id: 'a', type: 'uml_class',
  position: { x: 0, y: 0 }, data: { name: 'Cliente', attributes: [], methods: [] } }], edges: [], metadata: { viewport: null } })
function setup(t) {
  const messages = []
  const socket = { send: raw => messages.push(JSON.parse(raw)), close: () => {} }
  const client = new CollaborationClient({ url: 'ws://test', token: 'test', role: 'EDITOR', notify: () => {}, socketFactory: () => socket })
  t.after(() => client.stop()); client.start()
  const snapshot = (doc, op_id = null) => client.receive({ type: 'snapshot', document: doc, op_id, role: 'EDITOR' })
  snapshot(diagram())
  return { client, messages, snapshot }
}

test('save indicator waits for acknowledgement and preserves later unsent edits', t => {
  const { client, messages, snapshot } = setup(t)
  let state
  client.notify = next => { state = next }
  client.emit()
  assert.equal(saveStatus(state).kind, 'saved')
  const rename = name => doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name } })) })
  client.edit(rename('Persona'))
  assert.equal(saveStatus(state).kind, 'pending')
  client.flush()
  const first = messages.at(-1)
  assert.equal(saveStatus(state).kind, 'syncing')
  client.edit(rename('Empresa'))
  snapshot({ ...first.document, version: 2 }, first.op_id)
  assert.equal(saveStatus(state).kind, 'pending')
  client.flush()
  const second = messages.at(-1)
  snapshot({ ...second.document, version: 3 }, second.op_id)
  assert.equal(saveStatus(state).label, 'Guardado · v3')
  client.socket.onclose({ code: 1006 })
  clearTimeout(client.retry)
  assert.equal(saveStatus(state).kind, 'offline')
})

test('reservation denied leaves canvas intact and does not downgrade editor', async t => {
  const { client, messages } = setup(t)
  const pending = client.reservationRequest('reserve', ['a'])
  const request = messages.at(-1)
  client.receive({ type: 'error', code: 'reserved', op_id: request.op_id, message: 'Clase reservada por Ana' })
  assert.equal(await pending, false)
  assert.equal(client.role, 'EDITOR')
  assert.equal(client.blocked, false)
  assert.equal(client.draft.nodes[0].data.name, 'Cliente')
})

test('finish keeps reservation until save acknowledgement', t => {
  const { client, messages, snapshot } = setup(t)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Persona' } })) }))
  client.finish()
  assert.equal(messages.at(-1).type, 'update')
  const update = messages.at(-1)
  assert.equal(messages.some(m => m.type === 'release'), false)
  snapshot({ ...update.document, version: 2 }, update.op_id)
  assert.equal(messages.at(-1).type, 'release')
})

test('disconnect resolves pending reservation without granting it', async t => {
  const { client } = setup(t)
  const pending = client.reservationRequest('reserve', ['a'])
  client.socket.onclose({ code: 1006 }); clearTimeout(client.retry)
  assert.equal(await pending, false)
  assert.equal(client.connectionId, null)
  assert.deepEqual(client.reservations, [])
})

test('independent fields merge and shared fields conflict', () => {
  const base = diagram(), draft = structuredClone(base), remote = structuredClone(base)
  draft.nodes[0].data.name = 'Persona'; remote.nodes[0].position.x = 50
  assert.equal(mergeDocuments(base, draft, remote).nodes[0].position.x, 50)
  remote.nodes[0].data.name = 'Empresa'
  assert.throws(() => mergeDocuments(base, draft, remote), /Conflicto/)
})

test('ack preserves typing performed while the previous change was in flight', t => {
  const { client, messages, snapshot } = setup(t)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Persona' } })) }))
  client.flush()
  const sent = messages.at(-1)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Empresa' } })) }))
  snapshot({ ...sent.document, version: 2 }, sent.op_id)
  assert.equal(client.draft.nodes[0].data.name, 'Empresa')
  assert.equal(client.base.nodes[0].data.name, 'Persona')
  assert.equal(client.blocked, false)
  client.flush(); assert.equal(messages.at(-1).document.version, 2)
})

test('remote conflict keeps draft and latest can be explicitly loaded', t => {
  const { client, snapshot } = setup(t)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Persona' } })) }))
  const remote = diagram(); remote.version = 2; remote.nodes[0].data.name = 'Empresa'
  snapshot(remote)
  assert.equal(client.blocked, true); assert.equal(client.draft.nodes[0].data.name, 'Persona')
  client.reload(); assert.equal(client.draft.nodes[0].data.name, 'Empresa'); assert.equal(client.blocked, false)
})

test('viewer cannot send changes and permissions update in session', t => {
  const { client, messages } = setup(t)
  client.receive({ type: 'presence', participants: [], role: 'VIEWER' })
  client.edit(doc => ({ ...doc, nodes: [] })); client.flush()
  assert.equal(messages.length, 0); assert.equal(client.draft.nodes.length, 1)
})

test('validation blocks retries until a further edit without dropping draft', t => {
  const { client, messages } = setup(t)
  client.edit(doc => ({ ...doc, nodes: [] })); client.flush()
  client.receive({ type: 'error', code: 'validation', message: 'Invalid', op_id: messages.at(-1).op_id })
  client.flush(); assert.equal(messages.length, 1); assert.deepEqual(client.draft.nodes, [])
  client.edit(() => { const d = diagram(); d.nodes[0].data.name = 'Persona'; return d })
  client.flush(); assert.equal(messages.length, 2)
})

test('node identifiers cannot mutate object prototypes', () => {
  const base = diagram(), draft = diagram()
  draft.nodes.push({ ...draft.nodes[0], id: '__proto__' })
  assert.equal(mergeDocuments(base, draft, base).nodes.length, 2)
})

test('offline edits rebase on the latest version after reconnection', t => {
  const { client, messages, snapshot } = setup(t)
  client.socket.onclose({ code: 1006 }); clearTimeout(client.retry)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Persona' } })) }))
  client.flush(); assert.equal(messages.length, 0)
  const remote = diagram(); remote.version = 2; remote.nodes[0].position.x = 300
  snapshot(remote)
  assert.equal(client.draft.nodes[0].data.name, 'Persona')
  assert.equal(client.draft.nodes[0].position.x, 300)
  client.flush(); assert.equal(messages.at(-1).base.version, 2)
})

test('broadcast received before ack is deferred and then incorporated', t => {
  const { client, messages, snapshot } = setup(t)
  client.edit(doc => ({ ...doc, nodes: doc.nodes.map(n => ({ ...n, data: { ...n.data, name: 'Persona' } })) }))
  client.flush(); const sent = messages.at(-1)
  const newer = structuredClone(sent.document); newer.version = 3; newer.nodes[0].position.x = 400
  snapshot(newer)
  assert.ok(client.pending)
  snapshot({ ...sent.document, version: 2 }, sent.op_id)
  assert.equal(client.base.version, 3)
  assert.equal(client.draft.nodes[0].data.name, 'Persona')
  assert.equal(client.draft.nodes[0].position.x, 400)
  assert.equal(client.blocked, false)
})

test('confirmed import replaces a clean canvas and an older HTTP response cannot undo a newer broadcast', t => {
  const { client, snapshot } = setup(t)
  const imported = diagram(); imported.version = 2; imported.nodes[0].data.name = 'Pedido'
  snapshot(imported)
  const newer = structuredClone(imported); newer.version = 3; newer.nodes[0].position.x = 300
  snapshot(newer)
  snapshot(imported)
  assert.equal(client.draft.nodes[0].data.name, 'Pedido')
  assert.equal(client.draft.nodes[0].position.x, 300)
  assert.equal(client.base.version, 3)
  assert.equal(client.blocked, false)
})
