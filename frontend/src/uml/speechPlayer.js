export function speechChunks(text) {
  const words = text.replace(/[`*_#]/g, '').trim().split(/\s+/)
  const chunks = []
  let chunk = ''
  for (const word of words) {
    if (chunk && chunk.length + word.length > 220) { chunks.push(chunk); chunk = '' }
    chunk += (chunk ? ' ' : '') + word
  }
  if (chunk) chunks.push(chunk)
  return chunks
}

export function createSpeechPlayer(synth, Utterance, onState, onError) {
  let generation = 0
  let current = null
  function stop() {
    generation++
    const owned = current !== null
    current = null
    if (owned) synth?.cancel()
    onState(false)
  }
  return {
    stop,
    speak(text) {
      stop()
      if (!synth || !Utterance) { onError('Este navegador no ofrece lectura de voz. Puedes continuar por texto.'); return }
      const queue = speechChunks(text)
      const id = generation
      function next() {
        if (id !== generation) return
        if (!queue.length) { current = null; onState(false); return }
        const utterance = new Utterance(queue.shift())
        current = utterance
        const voices = synth.getVoices().filter(v => /^es(?:-|$)/i.test(v.lang))
        utterance.voice = voices.find(v => v.localService) || voices[0] || null
        utterance.lang = utterance.voice?.lang || 'es-ES'
        utterance.rate = 1
        utterance.onend = next
        utterance.onerror = () => {
          if (id !== generation) return
          stop()
          onError('No pude reproducir la respuesta. Pulsa Escuchar para intentarlo de nuevo o continúa por texto.')
        }
        onState(true)
        try { synth.speak(utterance) } catch { utterance.onerror() }
      }
      next()
    },
  }
}
