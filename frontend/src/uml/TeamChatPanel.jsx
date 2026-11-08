import { useEffect, useRef, useState } from 'react'
import {
  fetchProjectMessages,
  postChatMessage,
  postHelpRequest,
  mergeIncomingMessage,
  mergeHistoryPage,
  hasIAMention,
  stripIAMention,
  generateIdempotencyKey,
  formatMessageTime
} from './teamChat.js'

function renderFormattedMarkdown(text) {
  if (!text) return null
  const lines = text.split('\n')
  const elements = []
  let tableRows = []
  let inCodeBlock = false
  let codeBuffer = []
  let codeLang = ''

  function flushTable() {
    if (tableRows.length === 0) return
    const isHeaderSeparator = (line) => /^\|?\s*:?-+:?\s*(\|:?-+:?\s*)+\|?$/.test(line.trim())
    const rows = tableRows.filter(r => !isHeaderSeparator(r))
    if (rows.length > 0) {
      const headerCols = rows[0].split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1 || arr.length <= 2)
      const dataRows = rows.slice(1).map(r => r.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1 || arr.length <= 2))

      elements.push(
        <div key={`table-${elements.length}`} className="my-2 overflow-x-auto rounded border border-outline-variant/60 shadow-xs">
          <table className="min-w-full text-[11px] font-code-sm border-collapse bg-surface-container-lowest">
            <thead className="bg-surface-container-high text-on-surface font-semibold border-b border-outline-variant/50">
              <tr>
                {headerCols.map((col, idx) => (
                  <th key={idx} className="px-2.5 py-1.5 text-left">{renderInline(col)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 text-on-surface-variant">
              {dataRows.map((row, rIdx) => (
                <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-transparent' : 'bg-surface-container-lowest/50'}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-2.5 py-1 text-left align-top">{renderInline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    tableRows = []
  }

  function flushCodeBlock() {
    if (!inCodeBlock) return
    elements.push(
      <pre key={`code-${elements.length}`} className="my-2 p-2.5 rounded bg-inverse-surface text-inverse-on-surface text-[10px] font-code-sm overflow-x-auto">
        <code>{codeBuffer.join('\n')}</code>
      </pre>
    )
    codeBuffer = []
    inCodeBlock = false
  }

  function renderInline(str) {
    if (!str) return null
    // Simple inline parser for bold **text**, inline code `code`, and @mentions
    const parts = []
    let rest = str
    let keyIdx = 0

    while (rest.length > 0) {
      const boldMatch = rest.match(/^(.*?)\*\*(.+?)\*\*(.*)$/)
      const codeMatch = rest.match(/^(.*?)`([^`]+)`(.*)$/)
      const atIaMatch = rest.match(/^(.*?)(@IA)(.*)$/i)

      let earliest = null
      let type = null
      let match = null

      if (boldMatch && (!earliest || boldMatch[1].length < earliest)) {
        earliest = boldMatch[1].length
        type = 'bold'
        match = boldMatch
      }
      if (codeMatch && (!earliest || codeMatch[1].length < earliest)) {
        earliest = codeMatch[1].length
        type = 'code'
        match = codeMatch
      }
      if (atIaMatch && (!earliest || atIaMatch[1].length < earliest)) {
        earliest = atIaMatch[1].length
        type = 'at_ia'
        match = atIaMatch
      }

      if (!type) {
        parts.push(<span key={keyIdx++}>{rest}</span>)
        break
      }

      if (match[1]) parts.push(<span key={keyIdx++}>{match[1]}</span>)

      if (type === 'bold') {
        parts.push(<strong key={keyIdx++} className="font-semibold text-on-surface">{match[2]}</strong>)
        rest = match[3]
      } else if (type === 'code') {
        parts.push(<code key={keyIdx++} className="px-1 py-0.5 rounded bg-surface-container-high text-secondary text-[10px] font-mono">{match[2]}</code>)
        rest = match[3]
      } else if (type === 'at_ia') {
        parts.push(
          <span key={keyIdx++} className="inline-flex items-center px-1 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed text-[10px] font-bold">
            @IA
          </span>
        )
        rest = match[3]
      }
    }

    return parts
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock()
      } else {
        flushTable()
        inCodeBlock = true
        codeLang = line.trim().slice(3)
      }
      continue
    }

    if (inCodeBlock) {
      codeBuffer.push(line)
      continue
    }

    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      tableRows.push(line)
      continue
    } else {
      flushTable()
    }

    if (!line.trim()) {
      elements.push(<div key={`spacer-${i}`} className="h-1.5" />)
      continue
    }

    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${i}`} className="font-bold text-[12px] text-primary mt-2 mb-1 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
          <span>{renderInline(line.slice(4))}</span>
        </h4>
      )
    } else if (line.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="font-bold text-[13px] text-on-surface mt-2.5 mb-1.5">
          {renderInline(line.slice(3))}
        </h3>
      )
    } else if (line.startsWith('# ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="font-bold text-sm text-on-surface mt-3 mb-1.5">
          {renderInline(line.slice(2))}
        </h2>
      )
    } else if (/^\s*[-*•]\s+/.test(line)) {
      const content = line.replace(/^\s*[-*•]\s+/, '')
      elements.push(
        <div key={`li-${i}`} className="flex items-start gap-1.5 pl-2 my-0.5 text-on-surface-variant text-[11px]">
          <span className="text-secondary select-none">•</span>
          <div className="flex-1">{renderInline(content)}</div>
        </div>
      )
    } else {
      elements.push(
        <p key={`p-${i}`} className="my-0.5 text-on-surface-variant text-[11px] leading-relaxed">
          {renderInline(line)}
        </p>
      )
    }
  }

  flushTable()
  flushCodeBlock()

  return <div className="space-y-0.5">{elements}</div>
}

export function TeamChatPanel({
  projectId,
  token,
  user,
  shared,
  selection = null,
  onClose,
  visible = true
}) {
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [activeHelpRequests, setActiveHelpRequests] = useState(new Map())
  const [filterAiOnly, setFilterAiOnly] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const chatContainerRef = useRef(null)
  const textareaRef = useRef(null)

  // Scroll to bottom smoothly on new messages
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages, activeHelpRequests])

  // Carga inicial del historial de mensajes
  useEffect(() => {
    let cancelled = false
    setLoadingHistory(true)

    fetchProjectMessages(projectId, token, { limit: 50 })
      .then(res => {
        if (cancelled) return
        const list = res?.messages || res?.items || []
        if (Array.isArray(list)) {
          setMessages(list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)))
        }
      })
      .catch(err => {
        if (!cancelled) setErrorMessage(err.message || 'Error al cargar mensajes del proyecto')
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })

    return () => { cancelled = true }
  }, [projectId, token])

  // Suscripción a eventos WebSocket del canal colaborativo
  useEffect(() => {
    if (!shared?.subscribe) return

    const unsubscribe = shared.subscribe(msg => {
      if (!msg || !msg.type) return

      if (msg.type === 'chat.message' && msg.message) {
        setMessages(prev => mergeIncomingMessage(prev, msg.message))
      } else if (msg.type === 'help.requested' && msg.help_request) {
        setActiveHelpRequests(prev => {
          const next = new Map(prev)
          next.set(msg.help_request.id, msg.help_request)
          return next
        })
      } else if (msg.type === 'help.processing' && msg.help_request_id) {
        setActiveHelpRequests(prev => {
          const next = new Map(prev)
          const existing = next.get(msg.help_request_id) || {}
          next.set(msg.help_request_id, { ...existing, id: msg.help_request_id, status: 'processing' })
          return next
        })
      } else if (msg.type === 'help.answered') {
        if (msg.message) {
          setMessages(prev => mergeIncomingMessage(prev, msg.message))
        }
        if (msg.help_request_id) {
          setActiveHelpRequests(prev => {
            const next = new Map(prev)
            next.delete(msg.help_request_id)
            return next
          })
        }
      } else if (msg.type === 'help.failed' && msg.help_request_id) {
        setActiveHelpRequests(prev => {
          const next = new Map(prev)
          const existing = next.get(msg.help_request_id) || {}
          next.set(msg.help_request_id, {
            ...existing,
            id: msg.help_request_id,
            status: 'failed',
            error: msg.error || 'Error procesando solicitud de ayuda'
          })
          return next
        })
      }
    })

    return () => unsubscribe()
  }, [shared])

  async function handleSendMessage(forceHelp = false) {
    const raw = inputText.trim()
    if (!raw && !forceHelp) return

    let content = raw
    if (forceHelp && !hasIAMention(content)) {
      content = `@IA ${content}`.trim()
    }

    if (!content) return

    setSending(true)
    setErrorMessage('')

    try {
      const created = await postChatMessage(projectId, token, content)
      setMessages(prev => mergeIncomingMessage(prev, created))
      setInputText('')
      if (textareaRef.current) textareaRef.current.focus()
    } catch (err) {
      setErrorMessage(err.message || 'Error al enviar mensaje')
    } finally {
      setSending(false)
    }
  }

  async function handleRetryHelp(helpRequestId, prompt) {
    setErrorMessage('')
    try {
      const key = generateIdempotencyKey()
      await postHelpRequest(projectId, token, {
        userPrompt: prompt || 'Reintento de consulta al Desarrollador Senior',
        idempotencyKey: key
      })
      setActiveHelpRequests(prev => {
        const next = new Map(prev)
        next.delete(helpRequestId)
        return next
      })
    } catch (err) {
      setErrorMessage(err.message || 'Error al reintentar solicitud de ayuda')
    }
  }

  function handleRequestHelpOnSelection() {
    if (!selection) return
    const selName = selection.name || (selection.kind === 'node' ? `la clase seleccionada (${selection.id})` : `la relación seleccionada`)
    const suggested = `@IA ¿Cómo puedo estructurar correctamente las relaciones y responsabilidades de ${selName}?`
    setInputText(suggested)
    if (textareaRef.current) textareaRef.current.focus()
  }

  function scrollToMessage(msgId) {
    if (!msgId) return
    const el = document.getElementById(`msg-${msgId}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('ring-2', 'ring-secondary', 'rounded-lg')
      setTimeout(() => el.classList.remove('ring-2', 'ring-secondary', 'rounded-lg'), 2500)
    }
  }

  const displayedMessages = filterAiOnly
    ? messages.filter(m => m.role === 'assistant' || hasIAMention(m.content))
    : messages

  return (
    <div className="flex flex-col h-full bg-surface-container-lowest text-on-surface border-l border-outline-variant/60 shadow-xl select-none">
      {/* Cabecera del Panel */}
      <div className="h-12 px-3 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary text-on-primary flex items-center justify-center shadow-xs">
            <span className="material-symbols-outlined text-[17px]">psychology</span>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-headline-sm text-xs font-bold text-on-surface">Chat &amp; Senior Dev IA</span>
              <span className="px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-secondary-fixed text-on-secondary-fixed">
                Mentoría UML
              </span>
            </div>
            <p className="text-[10px] text-on-surface-variant font-code-sm">
              Canal compartido ({shared?.participants?.length || 1} activos)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setFilterAiOnly(!filterAiOnly)}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
              filterAiOnly
                ? 'bg-secondary text-on-secondary'
                : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
            }`}
            title="Filtrar solo consultas y respuestas del Desarrollador Senior"
          >
            {filterAiOnly ? 'Solo IA' : 'Todos'}
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container text-on-surface-variant hover:text-error transition-colors"
              title="Cerrar chat de equipo"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          )}
        </div>
      </div>

      {/* Banner de selección activa si hay un elemento UML seleccionado */}
      {selection && (
        <div className="px-3 py-1.5 bg-secondary-container/30 border-b border-secondary/20 flex items-center justify-between text-[11px]">
          <span className="text-on-secondary-container truncate max-w-[220px]">
            Elemento seleccionado: <strong>{selection.name || selection.id}</strong>
          </span>
          <button
            type="button"
            onClick={handleRequestHelpOnSelection}
            className="text-[10px] font-semibold text-secondary hover:underline flex items-center gap-0.5"
          >
            <span className="material-symbols-outlined text-[13px]">help</span>
            <span>Preguntar sobre esto</span>
          </button>
        </div>
      )}

      {/* Lista de Mensajes (Timeline) */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0 select-text"
      >
        {loadingHistory && (
          <div className="flex items-center justify-center py-6 text-on-surface-variant text-[11px] gap-2">
            <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
            <span>Cargando historial colaborativo...</span>
          </div>
        )}

        {!loadingHistory && displayedMessages.length === 0 && (
          <div className="text-center py-8 px-4 text-on-surface-variant">
            <div className="w-12 h-12 rounded-full bg-surface-container-high mx-auto flex items-center justify-center mb-2 text-secondary">
              <span className="material-symbols-outlined text-[24px]">forum</span>
            </div>
            <p className="font-semibold text-xs text-on-surface">Canal de Chat del Proyecto</p>
            <p className="text-[11px] mt-1">
              Todos los miembros del equipo ven este chat. Escribe un mensaje normal o incluye <strong className="text-secondary">@IA</strong> para consultar al Desarrollador Senior.
            </p>
          </div>
        )}

        {displayedMessages.map(msg => {
          const isAssistant = msg.role === 'assistant'
          const isMe = msg.user_id === user?.id
          const hasMention = hasIAMention(msg.content)

          if (isAssistant) {
            return (
              <div
                key={msg.id}
                id={`msg-${msg.id}`}
                className="bg-surface-container-low border border-primary/30 rounded-xl p-3 shadow-xs space-y-1.5 transition-all"
              >
                {/* Cabecera del mensaje de la IA Senior */}
                <div className="flex items-center justify-between border-b border-outline-variant/30 pb-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-[11px]">
                      <span className="material-symbols-outlined text-[14px]">psychology</span>
                    </div>
                    <div>
                      <span className="font-bold text-xs text-primary">Desarrollador Senior IA</span>
                      <span className="text-[9px] text-on-surface-variant font-code-sm ml-1.5">Mentor UML 2.5</span>
                    </div>
                  </div>
                  <span className="text-[9px] text-on-surface-variant font-code-sm">
                    {formatMessageTime(msg.created_at)}
                  </span>
                </div>

                {/* Enlace o cita a la pregunta original */}
                {msg.reply_to_message_id && (
                  <button
                    type="button"
                    onClick={() => scrollToMessage(msg.reply_to_message_id)}
                    className="w-full text-left px-2 py-1 bg-surface-container-high/60 hover:bg-surface-container-high rounded border-l-2 border-secondary text-[10px] text-on-surface-variant flex items-center justify-between gap-1 transition-colors"
                    title="Ir a la pregunta del desarrollador"
                  >
                    <span className="truncate">
                      En respuesta a la consulta de {msg.metadata?.requester_name || 'un integrante'}: &quot;{msg.metadata?.user_prompt || 'Ver pregunta'}&quot;
                    </span>
                    <span className="material-symbols-outlined text-[13px] text-secondary flex-shrink-0">arrow_upward</span>
                  </button>
                )}

                {/* Contenido formateado de la respuesta senior */}
                <div className="text-[11px] text-on-surface pt-1 leading-relaxed">
                  {renderFormattedMarkdown(msg.content)}
                </div>

                {/* Footer de métricas y seguridad */}
                <div className="pt-1.5 border-t border-outline-variant/20 flex items-center justify-between text-[9px] text-on-surface-variant font-code-sm">
                  <span>Revisión de arquitectura humana requerida</span>
                  {msg.metadata?.model && <span>{msg.metadata.model}</span>}
                </div>
              </div>
            )
          }

          // Mensaje de usuario (humano)
          return (
            <div
              key={msg.id}
              id={`msg-${msg.id}`}
              className={`flex flex-col space-y-1 transition-all ${isMe ? 'items-end' : 'items-start'}`}
            >
              <div className="flex items-center gap-1.5 text-[10px] text-on-surface-variant">
                <span className="font-semibold text-on-surface">
                  {isMe ? 'Tú' : (msg.user_name || msg.user_email || 'Colaborador')}
                </span>
                <span>•</span>
                <span>{formatMessageTime(msg.created_at)}</span>
                {hasMention && (
                  <span className="px-1.5 py-0.2 rounded-full bg-secondary-fixed text-on-secondary-fixed font-bold text-[9px]">
                    Consulta a Senior Dev
                  </span>
                )}
              </div>

              <div
                className={`max-w-[88%] rounded-2xl px-3 py-2 text-[11px] leading-relaxed shadow-xs ${
                  isMe
                    ? 'bg-secondary text-on-secondary rounded-br-xs'
                    : 'bg-surface-container-high text-on-surface rounded-bl-xs'
                } ${hasMention ? 'border-2 border-secondary/60' : ''}`}
              >
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              </div>

              {!hasMention && !isAssistant && (
                <button
                  type="button"
                  onClick={() => {
                    const prompt = `@IA ¿Puedes revisar y asesorar sobre lo que menciona ${isMe ? 'mi mensaje' : msg.user_name || 'el compañero'}: "${msg.content}"?`
                    setInputText(prompt)
                    if (textareaRef.current) textareaRef.current.focus()
                  }}
                  className="text-[9px] text-on-surface-variant hover:text-secondary flex items-center gap-0.5 px-1 py-0.5"
                  title="Pedir ayuda a Senior Dev sobre este mensaje"
                >
                  <span className="material-symbols-outlined text-[11px]">smart_toy</span>
                  <span>Pedir consejo sobre esto</span>
                </button>
              )}
            </div>
          )
        })}

        {/* Indicadores de solicitudes de ayuda en curso */}
        {Array.from(activeHelpRequests.values()).map(req => (
          <div
            key={req.id}
            className={`p-2.5 rounded-xl border text-[11px] flex items-center justify-between gap-2 shadow-xs ${
              req.status === 'failed'
                ? 'bg-error-container/40 border-error text-on-error-container'
                : 'bg-secondary-container/40 border-secondary text-on-secondary-container animate-pulse'
            }`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className={`material-symbols-outlined text-[18px] ${req.status === 'failed' ? 'text-error' : 'animate-spin'}`}>
                {req.status === 'failed' ? 'error' : 'sync'}
              </span>
              <div className="truncate">
                <p className="font-semibold text-xs">
                  {req.status === 'failed' ? 'Fallo en la consulta al Senior Dev' : 'El Desarrollador Senior está analizando el diagrama...'}
                </p>
                <p className="text-[10px] opacity-80 truncate">
                  {req.error || req.user_prompt || 'Procesando contexto UML'}
                </p>
              </div>
            </div>

            {req.status === 'failed' && (
              <button
                type="button"
                onClick={() => handleRetryHelp(req.id, req.user_prompt)}
                className="px-2.5 py-1 bg-error text-on-error rounded font-semibold text-[10px] hover:bg-error/90 flex-shrink-0"
              >
                Reintentar
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Mensaje de error general si ocurre */}
      {errorMessage && (
        <div className="px-3 py-1.5 bg-error-container text-on-error-container text-[11px] flex items-center justify-between border-t border-error/30">
          <span className="truncate">{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage('')} className="text-on-error-container hover:text-error">
            <span className="material-symbols-outlined text-[14px]">close</span>
          </button>
        </div>
      )}

      {/* Sugerencias Rápidas */}
      <div className="px-3 py-1 bg-surface-container-low border-t border-outline-variant/30 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        <span className="text-[10px] text-on-surface-variant font-semibold flex-shrink-0">Sugerencias:</span>
        <button
          type="button"
          onClick={() => setInputText('@IA ¿Puedes revisar la consistencia técnica de las clases y relaciones actuales?')}
          className="px-2 py-0.5 rounded-full bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-[10px] font-medium whitespace-nowrap transition-colors"
        >
          🔍 Revisar consistencia
        </button>
        <button
          type="button"
          onClick={() => setInputText('@IA ¿Cuándo conviene usar composición vs agregación en nuestro caso?')}
          className="px-2 py-0.5 rounded-full bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-[10px] font-medium whitespace-nowrap transition-colors"
        >
          📐 Composición vs Agregación
        </button>
      </div>

      {/* Área de Entrada y Acciones */}
      <div className="p-2.5 bg-surface-container-low border-t border-outline-variant/40 flex flex-col gap-2 flex-shrink-0">
        <div className="relative">
          <textarea
            ref={textareaRef}
            rows={2}
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSendMessage(false)
              }
            }}
            placeholder="Escribe un mensaje al equipo o usa @IA para consultar al Senior Dev..."
            className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest text-on-surface border border-outline-variant/60 focus:border-secondary focus:outline-none text-[11px] resize-none leading-relaxed shadow-inner"
            disabled={sending}
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-[9px] text-on-surface-variant font-code-sm">
            Enter para enviar · Shift+Enter nueva línea
          </span>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={sending || !inputText.trim()}
              onClick={() => handleSendMessage(true)}
              className="flex items-center gap-1 px-3 py-1.5 bg-primary hover:bg-primary/90 text-on-primary rounded-lg text-xs font-semibold shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Solicitar explícitamente la asesoría del Desarrollador Senior IA"
            >
              <span className="material-symbols-outlined text-[15px]">psychology</span>
              <span>Solicitar ayuda a Senior Dev</span>
            </button>

            <button
              type="button"
              disabled={sending || !inputText.trim()}
              onClick={() => handleSendMessage(false)}
              className="flex items-center justify-center w-8 h-8 bg-secondary hover:bg-secondary/90 text-on-secondary rounded-lg shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Enviar mensaje al equipo"
            >
              <span className="material-symbols-outlined text-[16px]">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
