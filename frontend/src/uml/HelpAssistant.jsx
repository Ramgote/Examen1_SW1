import { useState } from 'react'
import { api } from '../api'
import { helpTopics } from './helpContent'

export function HelpAssistant({ open, onClose, projectId, token, onStartTour }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([{ role: 'assistant', content: '¡Hola! Soy la guía de UML Studio. Puedo enseñarte a utilizar el editor o responder preguntas sobre sus herramientas. No modificaré tu diagrama.' }])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!open) return null

  async function ask(value = question) {
    const prompt = value.trim()
    if (!prompt || busy) return
    setQuestion('')
    setError('')
    setMessages(previous => [...previous, { role: 'user', content: prompt }])
    setBusy(true)
    try {
      const result = await api(`/projects/${projectId}/assistant/help`, { token, method: 'POST', body: { question: prompt } })
      setMessages(previous => [...previous, { role: 'assistant', content: result.answer }])
    } catch (err) {
      setError(err.message || 'No se pudo obtener una respuesta.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="uml-help-panel" role="dialog" aria-label="Asistente de orientación UML Studio">
      <header className="flex items-center justify-between gap-2 p-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2"><span className="text-xl">✦</span><div><strong className="block text-sm">Guía de UML Studio</strong><span className="text-[10px] text-slate-500">Ayuda y aprendizaje · Gemini</span></div></div>
        <button type="button" onClick={onClose} className="p-1 text-slate-500" aria-label="Cerrar asistente">✕</button>
      </header>
      <div className="p-3 border-b border-slate-100">
        <button type="button" onClick={onStartTour} className="w-full rounded-lg bg-blue-600 text-white text-xs font-semibold px-3 py-2.5">▶ Iniciar recorrido interactivo</button>
        <p className="text-[10px] text-slate-500 mt-2">O elige un tema para aprender:</p>
        <div className="flex flex-wrap gap-1.5 mt-2">{helpTopics.map(topic => <button key={topic.id} type="button" onClick={() => void ask(topic.question)} className="rounded-full border border-slate-200 px-2.5 py-1 text-[10px] text-slate-700 hover:bg-slate-50">{topic.title}</button>)}</div>
      </div>
      <div className="uml-help-messages" aria-live="polite">
        {messages.map((message, index) => <div key={`${index}-${message.role}`} className={`uml-help-message ${message.role}`}>{message.content}</div>)}
        {busy && <div className="text-xs text-slate-500 px-2 py-2">Estoy preparando una explicación…</div>}
        {error && <div role="alert" className="text-xs text-red-700 bg-red-50 rounded-lg p-2">{error}</div>}
      </div>
      <form className="p-3 border-t border-slate-200 flex gap-2" onSubmit={event => { event.preventDefault(); void ask() }}>
        <input value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ej. ¿Cómo agrego una relación?" maxLength={1500} className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-200" />
        <button disabled={busy || !question.trim()} type="submit" className="rounded-lg bg-blue-600 text-white px-3 text-xs font-semibold disabled:opacity-40">Enviar</button>
      </form>
    </aside>
  )
}
