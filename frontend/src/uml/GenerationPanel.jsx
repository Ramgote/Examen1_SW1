import { useState } from 'react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function GenerationPanel({ projectId, token, shared, exchangeBusy }) {
  const [target, setTarget] = useState('solution')
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const version = shared.diagram?.version
  const ready = shared.ready && !shared.pending && !shared.dirty && !shared.blocked && !exchangeBusy && !busy

  async function request(download = false) {
    if (!ready) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await fetch(`${BASE}/api/v1/projects/${projectId}/generate/${target}${download ? '' : '/validate'}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ expected_version: version }),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.errors?.join(' ') || 'No se pudo generar el backend')
      }
      if (download) {
        const url = URL.createObjectURL(await response.blob())
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = `${target}-${projectId}-v${version}.zip`
        anchor.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        setNotice(`Proyecto ZIP generado desde la versión v${version}. Extrae el archivo y sigue su README.md.`)
      } else {
        setReport(await response.json())
      }
    } catch (err) {
      setError(err.message)
      setReport(null)
    } finally {
      setBusy(false)
    }
  }

  const stackPills = [
    { name: 'Java 21', icon: 'coffee' },
    { name: 'Spring Boot 3.x', icon: 'bolt' },
    { name: 'Spring Data JPA / Hibernate', icon: 'database' },
    { name: 'PostgreSQL Driver', icon: 'storage' },
    { name: 'REST CRUD Controllers', icon: 'api' },
    { name: 'Maven', icon: 'build' },
  ]

  return (
    <div className="flex flex-col gap-4 font-sans text-xs text-on-surface select-none">
      <label className="flex flex-col gap-2">
        Artefactos a generar
        <select aria-label="Artefactos a generar" disabled={busy} value={target}
          onChange={(event) => { setTarget(event.target.value); setReport(null); setNotice(''); setError('') }}>
          <option value="solution">Spring Boot + Flutter Android</option>
          <option value="spring">Solo Spring Boot</option>
        </select>
        {target === 'solution' && <span>App Android con asistente por texto. Voz local pendiente.</span>}
      </label>
      {/* Resumen del Stack Arquitectural */}
      <div className="bg-surface-container-low p-3.5 rounded-xl border border-outline-variant/40 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-[22px]">layers</span>
            <div>
              <h4 className="font-headline-sm text-xs font-bold text-on-surface">
                Generador Spring Boot + Flutter Android
              </h4>
              <p className="text-[11px] text-on-surface-variant">
                Transformación canónica y determinista de clases UML a código Java ejecutable con persistencia relacional.
              </p>
            </div>
          </div>
          <span className="px-2.5 py-1 bg-secondary text-on-secondary rounded-full font-bold text-[10px] font-mono shadow-xs">
            v{version}
          </span>
        </div>

        {/* Badges de Stack */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {stackPills.map((pill, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-surface-container-highest text-on-surface rounded-full text-[10px] font-code-sm flex items-center gap-1 border border-outline-variant/30"
            >
              <span className="material-symbols-outlined text-[12px] text-secondary">{pill.icon}</span>
              {pill.name}
            </span>
          ))}
        </div>
      </div>

      {/* Alertas */}
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

      {/* Informe de Validación Arquitectural */}
      {report && (
        <div className="bg-surface-container-lowest border border-outline-variant/50 rounded-xl p-3 shadow-md flex flex-col gap-2.5">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                  report.valid
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                }`}
              >
                {report.valid ? '✓ MODELO COMPATIBLE' : '✕ REQUIERE CORRECCIONES'}
              </span>
              <span className="font-bold text-on-surface text-xs">
                Validación {target === 'solution' ? 'Spring + Flutter' : 'Spring Boot'} (v{report.version})
              </span>
            </div>
            {report.version !== version && (
              <span className="text-[10px] text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded">
                Desactualizado vs v{version}
              </span>
            )}
          </div>

          {/* Errores */}
          {report.errors?.length > 0 && (
            <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-900 rounded-lg flex flex-col gap-1 text-[11px]">
              <strong className="flex items-center gap-1 font-semibold text-rose-800">
                <span className="material-symbols-outlined text-[15px]">cancel</span>
                Errores bloqueantes ({report.errors.length}):
              </strong>
              <ul className="list-disc list-inside pl-1 space-y-0.5 font-mono text-[10px]">
                {report.errors.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Advertencias */}
          {report.warnings?.length > 0 && (
            <div className="p-2.5 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg flex flex-col gap-1 text-[11px]">
              <strong className="flex items-center gap-1 font-semibold text-amber-800">
                <span className="material-symbols-outlined text-[15px]">info</span>
                Avisos arquitecturales ({report.warnings.length}):
              </strong>
              <ul className="list-disc list-inside pl-1 space-y-0.5 text-[10px]">
                {report.warnings.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {report.valid && (
            <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg text-[11px]">
              Todas las validaciones de tipo JPA, unicidad, herencia simple y multiplicidades fueron aprobadas. El código fuente está listo para ser empaquetado y descargado.
            </div>
          )}
        </div>
      )}

      {/* Botones de Acción */}
      <div className="flex items-center justify-between pt-2 border-t border-outline-variant/30">
        <span className="text-[11px] text-on-surface-variant font-mono">
          {busy ? 'Procesando modelo con AST Transformer…' : 'Paso 1: Validar • Paso 2: Descargar ZIP'}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={!ready}
            onClick={() => request(false)}
            className="px-3.5 py-1.5 rounded-lg border border-outline-variant/60 hover:bg-surface-container text-on-surface font-semibold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-40"
          >
            <span className="material-symbols-outlined text-[16px] text-secondary">fact_check</span>
            <span>Validar Modelo</span>
          </button>

          <button
            type="button"
            disabled={!ready || !report?.valid || report.version !== version}
            onClick={() => request(true)}
            className="px-4 py-1.5 bg-secondary hover:bg-secondary/90 text-on-secondary font-semibold rounded-lg flex items-center gap-1.5 shadow-sm hover:shadow-md transition-all text-xs disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[16px]">download</span>
            <span>Descargar ZIP</span>
          </button>
        </div>
      </div>
    </div>
  )
}
