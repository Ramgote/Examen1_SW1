import test from 'node:test'
import assert from 'node:assert/strict'
import { canApplyProposal, mediaType, validateFiles } from './assistant.js'

test('proposal requires a clean editable canvas at exactly the reviewed version', () => {
  const proposal = { version: 2, changes: [{ action: 'add' }] }
  const shared = { diagram: { version: 2 }, role: 'EDITOR', ready: true, dirty: false, pending: false, blocked: false }
  assert.equal(canApplyProposal(proposal, shared), true)
  for (const change of [{ role: 'VIEWER' }, { dirty: true }, { pending: true }, { blocked: true }, { ready: false }, { diagram: { version: 3 } }]) {
    assert.equal(canApplyProposal(proposal, { ...shared, ...change }), false)
  }
  assert.equal(canApplyProposal({ ...proposal, changes: [] }, shared), false)
})

test('attachments enforce count size format and aliases before reading base64', () => {
  const png = { name: 'diagram.png', type: 'image/png', size: 1024 }
  const voice = { name: 'voice.webm', type: 'audio/webm;codecs=opus', size: 1024 }
  validateFiles([png, png, png, voice])
  assert.equal(mediaType(voice), 'audio/webm')
  assert.equal(mediaType({ type: 'audio/x-wav' }), 'audio/wav')
  for (const files of [[png, png, png, png], [voice, voice], [{ ...png, type: 'text/html' }],
    [{ ...png, size: 5 * 1024 * 1024 }], [{ ...png, size: 0 }],
    [{ ...png, size: 4 * 1024 * 1024 }, { ...voice, size: 6 * 1024 * 1024 }]]) {
    assert.throws(() => validateFiles(files))
  }
})
