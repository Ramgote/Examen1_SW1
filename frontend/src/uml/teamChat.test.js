import test from 'node:test'
import assert from 'node:assert/strict'
import {
  generateIdempotencyKey,
  hasIAMention,
  stripIAMention,
  mergeIncomingMessage,
  mergeHistoryPage,
  formatMessageTime
} from './teamChat.js'

test('generateIdempotencyKey creates unique non-empty strings', () => {
  const k1 = generateIdempotencyKey()
  const k2 = generateIdempotencyKey()
  assert.ok(k1 && k1.length > 5)
  assert.ok(k2 && k2.length > 5)
  assert.notEqual(k1, k2)
})

test('hasIAMention identifies reactive triggers correctly', () => {
  assert.equal(hasIAMention('@IA hola'), true)
  assert.equal(hasIAMention('hola @ia'), true)
  assert.equal(hasIAMention('consulta @IA: como relaciono?'), true)
  assert.equal(hasIAMention('@IA'), true)
  assert.equal(hasIAMention('usuario@ia.com'), false)
  assert.equal(hasIAMention('guia rapida'), false)
  assert.equal(hasIAMention(''), false)
  assert.equal(hasIAMention(null), false)
})

test('stripIAMention cleans prefix and spaces', () => {
  assert.equal(stripIAMention('@IA ¿Cómo relaciono A con B?'), '¿Cómo relaciono A con B?')
  assert.equal(stripIAMention('Hola @ia como estas'), 'Hola como estas')
  assert.equal(stripIAMention('@IA'), '')
})

test('mergeIncomingMessage deduplicates and sorts chronologically', () => {
  const m1 = { id: 'm1', content: 'Primero', created_at: '2026-10-28T10:00:00Z' }
  const m2 = { id: 'm2', content: 'Segundo', created_at: '2026-10-28T10:01:00Z' }
  const m3 = { id: 'm3', content: 'Tercero', created_at: '2026-10-28T10:02:00Z' }

  let list = [m1, m3]
  list = mergeIncomingMessage(list, m2)
  assert.equal(list.length, 3)
  assert.equal(list[0].id, 'm1')
  assert.equal(list[1].id, 'm2')
  assert.equal(list[2].id, 'm3')

  // Update existing message
  const m2Updated = { id: 'm2', content: 'Segundo Editado', created_at: '2026-10-28T10:01:00Z' }
  list = mergeIncomingMessage(list, m2Updated)
  assert.equal(list.length, 3)
  assert.equal(list[1].content, 'Segundo Editado')
})

test('mergeHistoryPage merges pagination without duplicates', () => {
  const m2 = { id: 'm2', content: 'Segundo', created_at: '2026-10-28T10:01:00Z' }
  const m3 = { id: 'm3', content: 'Tercero', created_at: '2026-10-28T10:02:00Z' }
  const olderPage = [
    { id: 'm1', content: 'Primero', created_at: '2026-10-28T10:00:00Z' },
    { id: 'm2', content: 'Segundo', created_at: '2026-10-28T10:01:00Z' }
  ]

  const merged = mergeHistoryPage([m2, m3], olderPage)
  assert.equal(merged.length, 3)
  assert.equal(merged[0].id, 'm1')
  assert.equal(merged[1].id, 'm2')
  assert.equal(merged[2].id, 'm3')
})

test('formatMessageTime returns valid hour:minute string', () => {
  const time = formatMessageTime('2026-10-28T14:35:00Z')
  assert.ok(time.length >= 4)
  assert.equal(formatMessageTime(''), '')
  assert.equal(formatMessageTime(null), '')
})

import { CollaborationClient } from './collaboration.js'

test('CollaborationClient subscribe receives chat and help WebSocket events and unsubscribes cleanly', () => {
  const received = []
  const client = new CollaborationClient({
    url: 'ws://test',
    token: 'test',
    role: 'EDITOR',
    notify: () => {},
    socketFactory: () => ({ send: () => {}, close: () => {} })
  })

  const unsubscribe = client.subscribe(msg => {
    received.push(msg)
  })

  // Simulate incoming WebSocket messages from the backend
  client.receive({ type: 'chat.message', message: { id: 'msg-1', content: 'Hola equipo' } })
  client.receive({ type: 'help.requested', help_request: { id: 'hr-1', status: 'pending' } })
  client.receive({ type: 'help.processing', help_request_id: 'hr-1' })
  client.receive({ type: 'help.answered', help_request_id: 'hr-1', message: { id: 'msg-2', content: 'Asesoría Senior' } })
  client.receive({ type: 'help.failed', help_request_id: 'hr-2', error: 'Timeout de API' })

  assert.equal(received.length, 5)
  assert.equal(received[0].type, 'chat.message')
  assert.equal(received[1].type, 'help.requested')
  assert.equal(received[2].type, 'help.processing')
  assert.equal(received[3].type, 'help.answered')
  assert.equal(received[4].type, 'help.failed')

  // Unsubscribe and verify no more events are delivered
  unsubscribe()
  client.receive({ type: 'chat.message', message: { id: 'msg-3', content: 'Otro mensaje' } })
  assert.equal(received.length, 5)
})
