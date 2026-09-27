import test from 'node:test'
import assert from 'node:assert/strict'
import { recentHistory, proposalReply } from './assistantConversation.js'

test('conversation context is bounded and never forwards attachments', () => {
  const messages = Array.from({ length: 10 }, (_, i) => ({ role: i % 2 ? 'assistant' : 'user', content: `${i}`.repeat(4000), attachments: ['private-audio'] }))
  const history = recentHistory(messages)
  assert.equal(history.length, 6)
  assert.equal(history[0].content[0], '4')
  assert.equal(history[0].content.length, 3000)
  assert.deepEqual(Object.keys(history[0]), ['role', 'content'])
  assert.equal(messages[0].content.length, 4000)
})

test('conversation distinguishes clarification from unapplied proposal', () => {
  assert.match(proposalReply({ message: '¿Qué clases?', changes: [] }), /No he propuesto cambios/)
  assert.match(proposalReply({ message: 'Crear Cliente', changes: [{}] }), /Todavía no están aplicados/)
})
