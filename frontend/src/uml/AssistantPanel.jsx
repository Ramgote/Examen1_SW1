import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { canApplyProposal, encodeFile, IMAGE_TYPES, mediaType, validateFiles } from './assistant'
import { useVoiceRecorder } from './useVoiceRecorder'
import { useAssistantSpeech } from './useAssistantSpeech'
import { relations } from './document'
import { welcome, recentHistory, proposalReply } from './assistantConversation'

function AttachmentCard({ file, remove, disabled }) {
  const media = useRef(null)
  const isImage = IMAGE_TYPES.includes(mediaType(file))

  useEffect(() => {
    const next = URL.createObjectURL(file)
    if (media.current) media.current.src = next
    return () => URL.revokeObjectURL(next)
  }, [file])

  return (
    <div className="relative group bg-surface-container-low border border-outline-variant/50 rounded-lg p-2 flex items-center gap-2 max-w-[240px] shadow-xs">
      <div className="w-10 h-10 rounded bg-surface-container-high flex items-center justify-center overflow-hidden flex-shrink-0">
        {isImage ? (
          <img ref={media} alt={`Adjunto: ${file.name}`} className="w-full h-full object-cover" />
        ) : (
          <span className="material-symbols-outlined text-secondary text-[20px]">mic</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-code-sm text-[11px] font-semibold text-on-surface truncate" title={file.name}>
          {file.name}
        </p>
        <p className="font-code-sm text-[9px] text-on-surface-variant">
          {(file.size / 1024).toFixed(0)} KiB • {isImage ? 'Imagen' : 'Audio'}
        </p>
        {!isImage && (
          <audio ref={media} controls className="h-5 w-full mt-1" preload="metadata" />
        )}
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={remove}
        className="text-on-surface-variant hover:text-error hover:bg-error-container/40 p-1 rounded-full transition-colors"
        title="Quitar archivo"
      >
        <span className="material-symbols-outlined text-[16px]">close</span>
      </button>
    </div>
  )
}

function RecordingDuration() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [])
  return <span className="text-[11px]">Detener ({seconds}s)</span>
}

function ElementDetails({ value, kind, names }) {
  if (!value) return <p className="text-on-surface-variant/70 italic text-[11px]">No existe en esta versión.</p>
  if (kind === 'class') {
    return (
      <div className="flex flex-col gap-1 text-[11px] font-code-sm">
        <div className="font-bold text-on-surface flex items-center gap-1">
          <span className="text-secondary">{value.data.package_name}.</span>
          <span>{value.data.name}</span>
          {value.data.is_abstract && <span className="text-on-surface-variant font-normal italic">(abstracta)</span>}
        </div>
        {value.data.attributes?.length > 0 && (
          <div className="pl-2 border-l border-outline-variant/40 flex flex-col gap-0.5">
            <span className="text-[10px] text-on-surface-variant font-semibold">Atributos:</span>
            {value.data.attributes.map(a => (
              <div key={a.name} className="flex items-center gap-1 text-[10px]">
                <strong className={a.visibility === '+' ? 'text-emerald-600' : a.visibility === '-' ? 'text-rose-600' : 'text-amber-600'}>
                  {a.visibility}
                </strong>
                <span>{a.name}: {a.type}</span>
                {a.is_pk && <span className="px-1 bg-secondary-fixed text-on-secondary-fixed rounded text-[8px] font-bold">PK</span>}
                {!a.is_nullable && <span className="text-[8px] text-on-surface-variant">req</span>}
              </div>
            ))}
          </div>
        )}
        {value.data.methods?.length > 0 && (
          <div className="pl-2 border-l border-outline-variant/40 flex flex-col gap-0.5">
            <span className="text-[10px] text-on-surface-variant font-semibold">Métodos:</span>
            {value.data.methods.map((m, i) => (
              <div key={i} className="flex items-center gap-1 text-[10px]">
                <strong className={m.visibility === '+' ? 'text-emerald-600' : m.visibility === '-' ? 'text-rose-600' : 'text-amber-600'}>
                  {m.visibility}
                </strong>
                <span>{m.name}({m.parameters.map(p => `${p.name}: ${p.param_type}`).join(', ')}): {m.return_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  return (
    <div className="text-[11px] font-code-sm text-on-surface flex flex-col gap-0.5">
      <div className="font-semibold text-secondary">
        {relations[value.type] || value.type}
      </div>
      <div className="text-[10px] text-on-surface-variant">
        <span>{names[value.source] || value.source} ({value.source_cardinality}{value.source_role ? `, rol: ${value.source_role}` : ''})</span>
        <span className="mx-1">→</span>
        <span>{names[value.target] || value.target} ({value.target_cardinality}{value.target_role ? `, rol: ${value.target_role}` : ''})</span>
      </div>
    </div>
  )
}

export function AssistantPanel({ projectId, token, shared, externalBusy, onBusy, visible = true }) {
  const speech = useAssistantSpeech(visible)
  const requestInFlight = useRef(false)
  const [messages, setMessages] = useState([])
  const [phase, setPhase] = useState('')
  const chatEnd = useRef(null)
  const promptRef = useRef(null)
  function say(role, content, spoken = content) {
    setMessages(previous => [...previous, { role, content }].slice(-30))
    if (role === 'assistant') speech.speak(spoken)
  }
  useEffect(() => { chatEnd.current?.scrollIntoView({ block: 'nearest' }) }, [messages, phase])

  const [config, setConfig] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [files, setFiles] = useState([])
  const [proposal, setProposal] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [showJsonRaw, setShowJsonRaw] = useState(false)

  const mounted = useRef(true)
  const filesRef = useRef([])
  const resultRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!proposal && !error && !notice) return
    resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [proposal, error, notice])

  useEffect(() => {
    mounted.current = true
    let active = true
    api(`/projects/${projectId}/assistant/status`, { token })
      .then(value => { if (active) setConfig(value) })
      .catch(err => { if (active) setError(err.message) })
    return () => { active = false; mounted.current = false }
  }, [projectId, token])

  function setAttachments(next) {
    filesRef.current = next
    setFiles(next)
  }

  function attach(nextFiles) {
    try {
      const next = [...filesRef.current, ...nextFiles]
      validateFiles(next)
      setAttachments(next)
      setError('')
      setProposal(null)
      return next
    } catch (err) {
      setError(err.message)
    }
  }

  const voice = useVoiceRecorder(file => {
    const next = attach([file])
    if (next) void propose(null, next)
  }, setError, visible)
  const recording = voice.state !== 'idle'

  const ready = shared.role !== 'VIEWER' && shared.ready && !shared.pending && !shared.dirty && !shared.blocked && !externalBusy && !busy

  function working(value) {
    setBusy(value)
    onBusy(value)
  }

  async function propose(event, recordedFiles = null) {
    event?.preventDefault()
    if (!visible || !ready || (!recordedFiles && recording) || !config?.configured || requestInFlight.current) return
    requestInFlight.current = true
    speech.stop()
    const submittedFiles = recordedFiles || files
    working(true)
    setPhase('Estoy revisando tu solicitud y el diagrama. Te responderé aquí en cuanto termine.')
    const history = recentHistory(messages)
    say('user', [prompt.trim(), ...submittedFiles.map(f => `Adjunto: ${f.name}`)].filter(Boolean).join('\n'))
    setError('')
    setNotice('')
    setProposal(null)
    const requestedVersion = shared.diagram.version
    try {
      validateFiles(submittedFiles)
      const attachments = await Promise.all(submittedFiles.map(encodeFile))
      const result = await api(`/projects/${projectId}/assistant/preview`, {
        token,
        method: 'POST',
        body: { expected_version: requestedVersion, prompt, attachments, history },
      })
      if (mounted.current) {
        setProposal(result)
        say('assistant', (result.transcript ? `Entendí este audio: «${result.transcript}».\n` : '') + proposalReply(result), proposalReply(result))
        setPrompt('')
        setAttachments([])
      }
    } catch (err) {
      if (mounted.current) { setError(err.message); say('assistant', 'No pude completar esta solicitud. ' + err.message) }
    } finally {
      requestInFlight.current = false
      if (mounted.current) { working(false); setPhase('') }
    }
  }

  async function apply() {
    if (!ready || recording || !canApplyProposal(proposal, shared)) return
    if (!proposal.changes.length) return
    const removed = proposal.changes.filter(c => c.action === 'delete').length
    if (!window.confirm(`¿Aplicar ${proposal.changes.length} cambios al diagrama compartido?${removed ? ` Se eliminarán ${removed} elementos.` : ''}`)) return
    working(true)
    setPhase('Estoy guardando los cambios que confirmaste.')
    setError('')
    try {
      const saved = await api(`/projects/${projectId}/canvas`, {
        token,
        method: 'PUT',
        body: proposal.document,
        sessionId: shared.connectionId,
      })
      if (!mounted.current) return
      shared.acceptSaved(saved)
      say('assistant', `Listo: los cambios se guardaron en la versión ${saved.version}. ¿Quieres revisar alguna relación o añadir algo más?`)
      setProposal(null)
      setNotice(`Cambios aplicados y guardados exitosamente. Versión ${saved.version}.`)
    } catch (err) {
      if (mounted.current) {
        const message = err.status === 409 ? 'El diagrama cambió. Vuelve a pedir una propuesta sobre la versión actual.' : err.message
        setError(message)
        say('assistant', 'No pude confirmar el guardado. ' + message)
      }
    } finally {
      if (mounted.current) { working(false); setPhase('') }
    }
  }

  const names = Object.fromEntries((shared.diagram?.nodes || []).map(n => [n.id, n.data.name]))
  const nextNames = Object.fromEntries((proposal?.document.nodes || []).map(n => [n.id, n.data.name]))

  const quickPrompts = [
    'Crea entidades Cliente y Pedido con relación 1 a N',
    'Ayúdame a decidir la multiplicidad entre Cliente y Pedido',
    'Crea jerarquía de herencia para Empleado y Gerente',
  ]

  return (
    <div className="flex flex-col gap-3 font-sans text-xs text-on-surface select-none">
      <section aria-label="Conversación con el asistente" className="rounded-xl border border-outline-variant/50 bg-surface-container-lowest p-3">
        <p className="font-semibold text-secondary mb-2">Asistente UML</p>
        <p className="leading-relaxed select-text">{welcome}</p>
        <div className="flex flex-wrap gap-2 my-2">
          <button type="button" disabled={!speech.supported || recording} aria-pressed={speech.enabled}
            className="rounded border px-2 py-1 disabled:opacity-40"
            onClick={() => speech.enabled ? speech.disable() : speech.enable(welcome)}>
            {speech.enabled ? 'Silenciar respuestas' : 'Activar voz y escuchar saludo'}
          </button>
          <button type="button" disabled={!speech.speaking} onClick={speech.stop}
            className="rounded border px-2 py-1 disabled:opacity-40">Detener audio</button>
        </div>
        {!speech.supported && <p role="status">La lectura de voz no está disponible en este navegador. Puedes usar texto y adjuntar audio.</p>}
        {speech.error && <p role="status">{speech.error}</p>}
        {speech.speaking && <p role="status">El asistente está hablando…</p>}
        <p className="text-[11px]">Pulsa Hablar, haz tu pregunta y luego Terminar y enviar. Responderé en voz alta. El micrófono sólo se activa cuando lo solicitas.</p>
        <div role="log" aria-live="polite" aria-relevant="additions" className="mt-3 max-h-64 overflow-y-auto flex flex-col gap-2 select-text">
          {messages.map((message, index) => (
            <div key={index} className={`rounded-lg p-2 whitespace-pre-wrap break-words ${message.role === 'user' ? 'bg-secondary-fixed text-on-secondary-fixed ml-4' : 'bg-surface-container-low mr-4'}`}>
              <strong className="block mb-1">{message.role === 'user' ? 'Tú' : 'Asistente'}</strong>
              {message.content}
              {message.role === 'assistant' && speech.supported && (
                <button type="button" disabled={recording || busy} className="block mt-1 underline disabled:opacity-40"
                  onClick={() => speech.enable(message.content)}>Escuchar respuesta</button>
              )}
            </div>
          ))}
          <div ref={chatEnd} />
        </div>
        {phase && <p role="status" className="mt-2 text-secondary animate-pulse">{phase}</p>}
        <p className="mt-2 text-[10px] text-on-surface-variant">La conversación es temporal. Adjunta de nuevo los archivos que quieras volver a consultar.</p>
      </section>
      {/* Estado del Backend Gemini */}
      {config && !config.configured && (
        <div role="status" className="p-2.5 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-amber-600 text-[18px]">warning</span>
          <div className="flex-1 text-[11px]">
            <strong>Falta configurar Gemini:</strong> Añade <code className="font-mono bg-amber-100 px-1 py-0.5 rounded text-[10px]">GEMINI_API_KEY</code> en <code className="font-mono bg-amber-100 px-1 py-0.5 rounded text-[10px]">backend/.env</code> y reinicia el servicio.
          </div>
        </div>
      )}

      {shared.role === 'VIEWER' && (
        <div className="p-2 bg-surface-container-high rounded text-on-surface-variant text-[11px] flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[15px]">lock</span>
          <span>Modo Lectura: Solo propietarios y editores pueden generar propuestas con IA.</span>
        </div>
      )}

      {/* Formulario Multimodal Principal */}
      <form onSubmit={propose} className="flex flex-col gap-2">
        <div className="relative">
          <textarea
            ref={promptRef}
            aria-label="Mensaje para el asistente UML"
            rows={3}
            maxLength={8000}
            value={prompt}
            disabled={busy || recording || externalBusy || shared.role === 'VIEWER'}
            placeholder="Describe en lenguaje natural los cambios arquitecturales, adjunta un boceto/diagrama o graba un comando de voz…"
            onChange={event => { setPrompt(event.target.value); setProposal(null) }}
            className="w-full p-2.5 bg-surface-container-low text-on-surface border border-outline-variant/60 rounded-lg font-sans text-xs outline-none focus:ring-1 focus:ring-secondary focus:bg-surface-container-lowest transition-all disabled:opacity-50 resize-y min-h-[70px]"
          />
          <div className="absolute right-2 bottom-2 text-[9px] text-on-surface-variant font-mono">
            {prompt.length}/8000
          </div>
        </div>

        {/* Sugerencias Rápidas */}
        {!prompt && files.length === 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            <span className="text-[10px] text-on-surface-variant font-semibold flex items-center gap-0.5 flex-shrink-0">
              <span className="material-symbols-outlined text-[13px] text-secondary">tips_and_updates</span>
              Ejemplos:
            </span>
            {quickPrompts.map((qp, i) => (
              <button
                key={i}
                type="button"
                disabled={!ready || recording}
                onClick={() => { setPrompt(qp); promptRef.current?.focus() }}
                className="px-2 py-0.5 bg-surface-container-high hover:bg-secondary-fixed hover:text-on-secondary-fixed text-on-surface-variant rounded-full text-[10px] transition-colors whitespace-nowrap"
              >
                {qp}
              </button>
            ))}
          </div>
        )}

        {/* Barra de Acciones y Adjuntos */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-outline-variant/30">
          <div className="flex items-center gap-1.5">
            {/* Input oculto de archivos */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/png,image/jpeg,image/webp,audio/wav,audio/mpeg,audio/ogg,audio/webm"
              disabled={!ready || recording}
              onChange={event => { attach(Array.from(event.target.files)); event.target.value = '' }}
              className="hidden"
            />

            {/* Botón Adjuntar */}
            <button
              type="button"
              disabled={!ready || recording}
              onClick={() => fileInputRef.current?.click()}
              className="px-2.5 py-1.5 rounded-lg border border-outline-variant/50 hover:bg-surface-container-high text-on-surface font-medium flex items-center gap-1 transition-colors disabled:opacity-40"
              title="Adjuntar diagramas PNG/JPEG/WebP o audios WAV/MP3"
            >
              <span className="material-symbols-outlined text-secondary text-[16px]">attach_file</span>
              <span className="text-[11px]">Adjuntar</span>
            </button>

            {/* Botón Grabar Voz */}
            {voice.state !== 'recording' ? (
              <button
                type="button"
                disabled={!ready || recording || !config?.configured || files.some(f => mediaType(f).startsWith('audio/'))}
                onClick={() => { if (speech.supported) speech.enable(''); speech.stop(); voice.start() }}
                className="px-2.5 py-1.5 rounded-lg border border-outline-variant/50 hover:bg-surface-container-high text-on-surface font-medium flex items-center gap-1 transition-colors disabled:opacity-40"
                title="Grabar comando de voz con micrófono"
              >
                <span className="material-symbols-outlined text-rose-600 text-[16px]">mic</span>
                <span className="text-[11px]">Hablar</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={voice.stop}
                className="px-2.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium flex items-center gap-1.5 transition-colors animate-pulse"
                title="Detener grabación"
              >
                <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
                <RecordingDuration />
                <span>Terminar y enviar</span>
              </button>
            )}

            {voice.state === 'requesting' && (
              <span className="text-[10px] text-secondary font-mono animate-pulse">
                Solicitando micrófono…
              </span>
            )}
          </div>

          {/* Botón Generar Propuesta */}
          <button
            type="submit"
            disabled={!ready || recording || !config?.configured || (!prompt.trim() && !files.length)}
            className="px-4 py-1.5 bg-secondary text-on-secondary rounded-lg font-semibold flex items-center gap-1.5 hover:shadow-md transition-all disabled:opacity-40 disabled:cursor-not-allowed text-[11px]"
          >
            {busy ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Procesando con Gemini…</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                <span>Enviar mensaje</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Lista de Adjuntos Cargados */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-outline-variant/30">
          {files.map((file, index) => (
            <AttachmentCard
              key={`${file.name}-${index}`}
              file={file}
              disabled={busy || recording || externalBusy}
              remove={() => {
                setAttachments(files.filter((_, i) => i !== index))
                setProposal(null)
              }}
            />
          ))}
        </div>
      )}

      {/* Mensajes de Notificación y Error */}
      {error && (
        <div role="alert" className="p-2.5 bg-rose-50 border border-rose-200 text-rose-900 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-rose-600 text-[18px]">error</span>
          <span className="text-[11px] font-mono flex-1">{error}</span>
        </div>
      )}

      {notice && (
        <div role="status" className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-emerald-600 text-[18px]">check_circle</span>
          <span className="text-[11px] font-medium flex-1">{notice}</span>
        </div>
      )}

      {proposal && !proposal.changes.length && proposal.warnings?.length > 0 && (
        <div role="status" className="rounded-lg p-2 bg-amber-50 text-amber-900">
          <strong>Ten en cuenta:</strong>
          <ul className="list-disc pl-4">{proposal.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>
        </div>
      )}

      {/* Tarjeta de Propuesta Recibida y Comparador de Diferencias */}
      {proposal && proposal.changes.length > 0 && (
        <div
          ref={resultRef}
          tabIndex={-1}
          className="bg-surface-container-low border border-secondary/40 rounded-xl p-3 shadow-md flex flex-col gap-3 outline-none"
        >
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant/40">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-secondary-fixed text-on-secondary-fixed rounded-full text-[10px] font-bold font-mono">
                Propuesta v{proposal.version}
              </span>
              <span className="font-bold text-on-surface text-[12px]">
                {proposal.changes.length} cambios propuestos
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setShowJsonRaw(v => !v)}
                className="px-2 py-1 bg-surface-container-high hover:bg-surface-container text-on-surface-variant rounded text-[10px] font-mono flex items-center gap-1"
                title="Inspeccionar JSON del documento resultante"
              >
                <span className="material-symbols-outlined text-[13px]">code</span>
                <span>{showJsonRaw ? 'Ocultar JSON' : 'Ver JSON'}</span>
              </button>
            </div>
          </div>

          {/* Explicación generada por Gemini */}
          {proposal.message && (
            <div className="p-2.5 bg-surface-container-lowest border border-outline-variant/40 rounded-lg text-[11px] text-on-surface leading-relaxed">
              <strong className="text-secondary block mb-0.5">Explicación del Asistente:</strong>
              {proposal.message}
            </div>
          )}

          {/* Transcripción de Audio si aplica */}
          {proposal.transcript && (
            <div className="p-2 bg-surface-container-high rounded text-[10px] text-on-surface-variant font-mono">
              <strong>Transcripción de audio:</strong> «{proposal.transcript}»
            </div>
          )}

          {/* Advertencias */}
          {proposal.warnings?.length > 0 && (
            <div className="p-2 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg flex flex-col gap-1">
              <span className="font-bold text-[10px] flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">warning</span>
                Advertencias del modelo:
              </span>
              <ul className="list-disc list-inside text-[10px] pl-1">
                {proposal.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {proposal.version !== shared.diagram?.version && (
            <div className="p-2 bg-rose-50 text-rose-800 border border-rose-200 rounded text-[11px] font-semibold">
              Esta propuesta se generó sobre la versión {proposal.version}, pero el diagrama actual está en la versión {shared.diagram?.version}. Solicita una nueva propuesta.
            </div>
          )}

          {/* Listado de Cambios con Diffs Detallados */}
          <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
            {proposal.changes.map(change => {
              const badgeColor =
                change.action === 'add'
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : change.action === 'update'
                  ? 'bg-blue-100 text-blue-800 border-blue-300'
                  : 'bg-rose-100 text-rose-800 border-rose-300'

              const actionLabel =
                change.action === 'add' ? '+ AÑADIR' : change.action === 'update' ? '~ MODIFICAR' : '- ELIMINAR'

              const targetName =
                change.after?.data?.name || change.before?.data?.name || change.id

              return (
                <details
                  key={`${change.kind}-${change.id}`}
                  className="bg-surface-container-lowest border border-outline-variant/40 rounded-lg p-2 group"
                >
                  <summary className="cursor-pointer font-semibold text-on-surface text-[11px] flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border ${badgeColor}`}>
                        {actionLabel}
                      </span>
                      <span>
                        {change.kind === 'class' ? 'Clase' : 'Relación'}: <strong className="text-secondary">{targetName}</strong>
                      </span>
                    </div>
                    <span className="material-symbols-outlined text-[15px] text-on-surface-variant group-open:rotate-180 transition-transform">
                      expand_more
                    </span>
                  </summary>

                  <div className="mt-2 pt-2 border-t border-outline-variant/30 grid grid-cols-2 gap-2">
                    <div className="bg-surface-container-low p-2 rounded">
                      <span className="font-bold text-[10px] text-on-surface-variant uppercase block mb-1">
                        Estado Anterior
                      </span>
                      <ElementDetails value={change.before} kind={change.kind} names={names} />
                    </div>
                    <div className="bg-surface-container-low p-2 rounded">
                      <span className="font-bold text-[10px] text-secondary uppercase block mb-1">
                        Propuesta Resultante
                      </span>
                      <ElementDetails value={change.after} kind={change.kind} names={nextNames} />
                    </div>
                  </div>
                </details>
              )
            })}
          </div>

          {/* Visor JSON Crudo */}
          {showJsonRaw && (
            <div className="p-2 bg-surface-container-high rounded border border-outline-variant/40 max-h-48 overflow-y-auto">
              <pre className="font-mono text-[10px] text-on-surface whitespace-pre-wrap">
                {JSON.stringify(proposal.document, null, 2)}
              </pre>
            </div>
          )}

          {/* Botones de Aplicación y Descarte */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-outline-variant/40">
            <button
              type="button"
              disabled={busy}
              onClick={() => { setProposal(null); say('assistant', 'Propuesta descartada. ¿Qué te gustaría cambiar de la solicitud?'); promptRef.current?.focus() }}
              className="px-3 py-1.5 rounded-lg border border-outline-variant/60 hover:bg-surface-container text-on-surface font-medium text-[11px] transition-colors"
            >
              Descartar propuesta
            </button>
            <button
              type="button"
              disabled={!ready || recording || !canApplyProposal(proposal, shared)}
              onClick={apply}
              className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold flex items-center gap-1.5 shadow-sm hover:shadow-md transition-all text-[11px] disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[16px]">check</span>
              <span>Aplicar cambios al diagrama</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
