import test from 'node:test'
import assert from 'node:assert/strict'
import { reloadDraft, saveStatus } from './saveStatus.js'

const saved = { ready: true, diagram: { version: 3 }, dirty: false, pending: false, blocked: false, error: '' }

test('saved label requires a loaded, connected, clean, acknowledged document', () => {
  assert.deepEqual(saveStatus(saved), { kind: 'saved', label: 'Guardado · v3' })
  for (const [change, kind] of [
    [{ dirty: true }, 'pending'],
    [{ pending: true }, 'syncing'],
    [{ ready: false }, 'offline'],
    [{ diagram: null }, 'pending'],
    [{ error: 'Reserva denegada' }, 'error'],
    [{ blocked: true }, 'error'],
    [{ dirty: true, pending: true, blocked: true }, 'error'],
    [{ ready: false, dirty: true, pending: true }, 'offline'],
  ]) assert.equal(saveStatus({ ...saved, ...change }).kind, kind)
})

test('cancelled recovery keeps draft and does not invoke reload', () => {
  let reloads = 0
  const state = { ...saved, dirty: true, diagram: { version: 3, nodes: [{ name: 'Local' }] }, reload: () => reloads++ }
  const before = structuredClone(state.diagram)
  assert.equal(reloadDraft(state, () => false), false)
  assert.equal(reloads, 0)
  assert.deepEqual(state.diagram, before)
  assert.equal(reloadDraft(state, () => true), true)
  assert.equal(reloads, 1)
})

test('recovery cannot discard a document while disconnected or awaiting acknowledgement', () => {
  for (const change of [{ ready: false }, { pending: true }, { diagram: null }]) {
    assert.equal(reloadDraft({ ...saved, dirty: true, ...change, reload: () => assert.fail('Unexpected reload') }, () => assert.fail('Unexpected confirmation')), false)
  }
  let reloaded = false
  assert.equal(reloadDraft({ ...saved, reload: () => { reloaded = true } }, () => assert.fail('Clean diagram does not need confirmation')), true)
  assert.equal(reloaded, true)
})
