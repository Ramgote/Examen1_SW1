import { useEffect, useRef, useState } from 'react'

export function useVoiceRecorder(onFile, onError, visible = true) {
  const session = useRef(null)
  const alive = useRef(true)
  const [state, setState] = useState('idle')
  useEffect(() => () => {
    const active = session.current
    if (!active) return
    active.cancelled = true
    clearTimeout(active.timer)
    active.stream?.getTracks().forEach(track => track.stop())
    if (active.recorder?.state === 'recording') active.recorder.stop()
  }, [visible])
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
      if (session.current) {
        session.current.cancelled = true
        clearTimeout(session.current.timer)
        session.current.stream?.getTracks().forEach(track => track.stop())
        if (session.current.recorder?.state === 'recording') session.current.recorder.stop()
      }
    }
  }, [])
  function stop() {
    const active = session.current
    if (!active) return
    clearTimeout(active.timer)
    if (active.recorder?.state === 'recording') active.recorder.stop()
    active.stream?.getTracks().forEach(track => track.stop())
  }
  async function start() {
    if (session.current) return
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      onError('Este navegador no permite grabar aquí. Usa HTTPS o localhost, o adjunta un archivo de audio.'); return
    }
    const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'].find(type => MediaRecorder.isTypeSupported(type))
    if (!mime) { onError('No hay un formato de grabación compatible. Adjunta un audio WAV, MP3, OGG o WebM.'); return }
    const active = { cancelled: false, chunks: [], size: 0 }
    session.current = active
    setState('requesting')
    try {
      active.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!alive.current || active.cancelled) {
        active.stream.getTracks().forEach(track => track.stop())
        session.current = null
        if (alive.current) setState('idle')
        return
      }
      active.recorder = new MediaRecorder(active.stream, { mimeType: mime })
      active.recorder.ondataavailable = event => {
        if (active.cancelled) return
        active.size += event.data.size
        if (active.size > 6 * 1024 * 1024) {
          active.cancelled = true; stop()
          if (alive.current) onError('El audio superó 6 MiB. Graba una instrucción más corta.')
        } else if (event.data.size) active.chunks.push(event.data)
      }
      active.recorder.onerror = () => {
        active.cancelled = true; stop()
        if (alive.current) onError('No se pudo completar la grabación.')
      }
      active.recorder.onstop = () => {
        clearTimeout(active.timer)
        active.stream.getTracks().forEach(track => track.stop())
        session.current = null
        if (!alive.current) return
        setState('idle')
        if (!active.cancelled && active.chunks.length) {
          const blob = new Blob(active.chunks, { type: mime.split(';')[0] })
          onFile(new File([blob], `comando-voz.${mime.includes('ogg') ? 'ogg' : 'webm'}`, { type: blob.type }))
        }
      }
      active.recorder.start(500)
      setState('recording')
      active.timer = setTimeout(stop, 60000)
    } catch {
      active.stream?.getTracks().forEach(track => track.stop())
      session.current = null
      if (alive.current) { setState('idle'); onError('No se pudo acceder al micrófono. Revisa su permiso o adjunta un audio.') }
    }
  }
  return { state, start, stop }
}
