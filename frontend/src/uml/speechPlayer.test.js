import test from 'node:test'
import assert from 'node:assert/strict'
import { createSpeechPlayer, speechChunks } from './speechPlayer.js'

function fixture() {
  const utterances = [], states = [], errors = []
  let cancelled = 0
  const voices = [{ lang: 'en-US', name: 'English' }, { lang: 'es-ES', name: 'Spanish', localService: true }]
  const synth = { getVoices: () => voices, speak: u => utterances.push(u), cancel: () => cancelled++ }
  class Utterance { constructor(text) { this.text = text } }
  const player = createSpeechPlayer(synth, Utterance, v => states.push(v), e => errors.push(e))
  return { player, utterances, states, errors, cancelled: () => cancelled }
}

test('speaks Spanish sequentially and preserves a long answer', () => {
  const f = fixture()
  const text = 'Esta es una respuesta con varias frases. '.repeat(30).trim()
  f.player.speak(text)
  for (let i = 0; i < f.utterances.length; i++) {
    assert.equal(f.utterances[i].lang, 'es-ES')
    assert.equal(f.utterances[i].voice.name, 'Spanish')
    f.utterances[i].onend()
  }
  assert.equal(f.utterances.map(u => u.text).join(' '), text)
  assert.equal(f.states.at(-1), false)
})

test('stop during speech prevents queued text and ignores late callbacks', () => {
  const f = fixture()
  f.player.speak('Texto largo. '.repeat(100))
  const old = f.utterances[0]
  f.player.stop()
  old.onend()
  old.onerror()
  assert.equal(f.utterances.length, 1)
  assert.equal(f.cancelled(), 1)
  assert.equal(f.errors.length, 0)
  f.player.speak('Nueva respuesta')
  old.onend()
  assert.equal(f.utterances.length, 2)
  assert.equal(f.utterances[1].text, 'Nueva respuesta')
})

test('audio error stops the queue and offers text fallback', () => {
  const f = fixture()
  f.player.speak('Texto largo. '.repeat(100))
  f.utterances[0].onerror()
  f.utterances[0].onend()
  assert.equal(f.utterances.length, 1)
  assert.equal(f.states.at(-1), false)
  assert.match(f.errors[0], /continúa por texto/)
})

test('missing browser API and empty text are handled', () => {
  const errors = []
  createSpeechPlayer(null, null, () => {}, e => errors.push(e)).speak('Hola')
  assert.equal(errors.length, 1)
  assert.deepEqual(speechChunks(''), [])
  assert.deepEqual(speechChunks('**Hola** `Cliente`'), ['Hola Cliente'])
})
