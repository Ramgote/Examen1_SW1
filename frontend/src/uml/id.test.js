import test from 'node:test'
import assert from 'node:assert/strict'
import { newId } from './id.js'

test('LAN HTTP can create UUID v4 without randomUUID', () => {
  const source = { getRandomValues: array => globalThis.crypto.getRandomValues(array) }
  const ids = Array.from({ length: 100 }, () => newId(source))
  assert.equal(new Set(ids).size, 100)
  for (const id of ids) assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
  assert.throws(() => newId({}), /identificadores seguros/)
})
