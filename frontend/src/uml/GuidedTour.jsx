import { useEffect, useState } from 'react'
import { tourSteps } from './helpContent'

export function GuidedTour({ open, onClose }) {
  const [index, setIndex] = useState(0)
  const [rect, setRect] = useState(null)
  const step = tourSteps[index]

  useEffect(() => {
    if (!open) return undefined
    const update = () => {
      const element = window.document.querySelector(step.target)
      if (!element) { setRect(null); return }
      const box = element.getBoundingClientRect()
      setRect({ top: box.top, left: box.left, width: box.width, height: box.height })
    }
    update()
    const timer = window.setTimeout(update, 80)
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [open, step])

  useEffect(() => { if (open) setIndex(0) }, [open])
  if (!open) return null

  return (
    <div className="uml-tour-layer" role="dialog" aria-modal="true" aria-labelledby="uml-tour-title">
      <div className="uml-tour-backdrop" />
      {rect && <div className="uml-tour-highlight" style={{ top: rect.top - 5, left: rect.left - 5, width: rect.width + 10, height: rect.height + 10 }} />}
      <section className="uml-tour-card">
        <div className="flex items-center justify-between gap-3 mb-3">
          <span className="text-[10px] uppercase tracking-wider font-bold text-blue-700">Recorrido guiado · {index + 1} de {tourSteps.length}</span>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-900" aria-label="Cerrar recorrido">✕</button>
        </div>
        <h2 id="uml-tour-title" className="text-base font-bold text-slate-900 mb-2">{step.title}</h2>
        <p className="text-sm leading-6 text-slate-600">{step.body}</p>
        {!rect && <p className="text-xs text-amber-700 mt-2">Esta sección no está visible en el tamaño actual de la ventana. Puedes continuar con la explicación.</p>}
        <div className="flex items-center justify-between gap-2 mt-5">
          <button type="button" onClick={() => setIndex(i => Math.max(0, i - 1))} disabled={index === 0} className="px-3 py-2 text-xs rounded-lg border border-slate-300 disabled:opacity-40">Anterior</button>
          <button type="button" onClick={onClose} className="px-3 py-2 text-xs rounded-lg text-slate-600 hover:bg-slate-100">Salir</button>
          {index < tourSteps.length - 1
            ? <button type="button" onClick={() => setIndex(i => i + 1)} className="px-4 py-2 text-xs rounded-lg bg-blue-600 text-white font-semibold">Siguiente</button>
            : <button type="button" onClick={onClose} className="px-4 py-2 text-xs rounded-lg bg-blue-600 text-white font-semibold">Finalizar</button>}
        </div>
      </section>
    </div>
  )
}
