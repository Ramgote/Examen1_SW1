import { useState, useRef } from 'react'
import { api } from '../api'
import { relations } from './document'

import { API_BASE as BASE } from '../apiBase'

async function exchange(path, token, file) {
  const response = await fetch(`${BASE}/api/v1${path}`, {
    method: file ? 'POST' : 'GET',
    headers: { Authorization: `Bearer ${token}`, ...(file ? { 'Content-Type': 'application/xml' } : {}) },
    ...(file ? { body: file } : {}),
  })
  if (!response.ok) {
    const data = await response.json()
    throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo procesar el archivo XMI')
  }
  return file ? response.json() : response.blob()
}

export function XmiPanel({ projectId, token, shared, onBusy, externalBusy = false }) {
  const [activeTab, setActiveTab] = useState('export') // 'export' | 'import'
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [exportFormat, setExportFormat] = useState('ea17')
  const fileInputRef = useRef(null)

  const editable = !externalBusy && shared.role !== 'VIEWER' && shared.ready && !shared.pending && !shared.dirty && !shared.blocked
  const path = `/projects/${projectId}`

  function working(value) {
    setBusy(value)
    onBusy(value)
  }

  async function previewFile(event) {
    const file = event.target.files[0]
    event.target.value = ''
    if (!file || !editable) return
    setPreview(null)
    setError('')
    setNotice('')
    if (file.size > 4 * 1024 * 1024) {
      setError('El archivo supera los 4 MiB permitidos.')
      return
    }
    working(true)
    try {
      setPreview(await exchange(`${path}/xmi/preview`, token, file))
    } catch (err) {
      setError(err.message)
    } finally {
      working(false)
    }
  }

  async function apply() {
    if (!editable || !preview || busy) return
    if (!window.confirm('Esta importación reemplazará todas las clases y relaciones del proyecto para todos los colaboradores. ¿Confirmar reemplazo?')) return
    working(true)
    setError('')
    try {
      const saved = await api(`${path}/canvas`, {
        token,
        method: 'PUT',
        body: preview.document,
        sessionId: shared.connectionId,
      })
      shared.acceptSaved(saved)
      setPreview(null)
      setNotice(`Importación aplicada y guardada exitosamente. Versión ${saved.version}.`)
    } catch (err) {
      setError(err.status === 409 ? 'Otro colaborador modificó el diagrama. Vuelve a cargar el archivo para revisar una nueva versión.' : err.message)
    } finally {
      working(false)
    }
  }

  async function download() {
    working(true)
    setError('')
    setNotice('')
    try {
      const blob = await exchange(`${path}/xmi?format=${exportFormat}`, token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `proyecto-${projectId}${exportFormat !== 'standard' ? '-' + exportFormat : ''}.xmi`
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      setNotice('Archivo XMI descargado exitosamente.')
    } catch (err) {
      setError(err.message)
    } finally {
      working(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 font-sans text-xs text-on-surface select-none">
      {/* Sub-pestañas de Exportación / Importación */}
      <div className="flex items-center gap-1 border-b border-outline-variant/40 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('export')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'export'
              ? 'bg-secondary text-on-secondary shadow-xs'
              : 'hover:bg-surface-container text-on-surface-variant'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">download</span>
          <span>Exportar a Enterprise Architect</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('import')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
            activeTab === 'import'
              ? 'bg-secondary text-on-secondary shadow-xs'
              : 'hover:bg-surface-container text-on-surface-variant'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">upload_file</span>
          <span>Importar archivo XMI</span>
        </button>
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

      {/* Pestaña: Exportar */}
      {activeTab === 'export' && (
        <div className="flex flex-col gap-3">
          <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/40 flex flex-col gap-2.5">
            <label className="font-code-sm text-[11px] font-semibold text-on-surface-variant">
              Formato de Exportación XMI
            </label>
            <select
              value={exportFormat}
              disabled={busy}
              onChange={event => setExportFormat(event.target.value)}
              className="px-2.5 py-1.5 bg-surface-container-lowest text-on-surface border border-outline-variant/60 rounded font-code-sm text-xs outline-none focus:ring-1 focus:ring-secondary"
            >
              <option value="ea17">Enterprise Architect 17.0 · XMI 2.1 con Diagrama de Clases visual</option>
              <option value="ea15">Enterprise Architect 15.0 · Compatibilidad anterior</option>
              <option value="standard">XMI 2.5.1 Estándar OMG · Modelo semántico canónico</option>
            </select>
            <p className="text-[11px] text-on-surface-variant leading-relaxed">
              Genera un paquete XML interoperable con coordenadas espaciales, clases, atributos, visibilidades, multiplicidades y diagramas listos para abrir en Sparx Enterprise Architect.
            </p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-on-surface-variant font-mono">
              Versión actual: v{shared.diagram?.version} ({shared.diagram?.nodes?.length || 0} clases, {shared.diagram?.edges?.length || 0} relaciones)
            </span>
            <button
              type="button"
              disabled={externalBusy || busy || !shared.ready || shared.dirty || shared.pending}
              onClick={download}
              className="px-4 py-2 bg-secondary hover:bg-secondary/90 text-on-secondary font-semibold rounded-lg flex items-center gap-1.5 shadow-sm hover:shadow-md transition-all text-xs disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[16px]">file_download</span>
              <span>Exportar XMI Guardado</span>
            </button>
          </div>
        </div>
      )}

      {/* Pestaña: Importar */}
      {activeTab === 'import' && (
        <div className="flex flex-col gap-3">
          <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/40 flex flex-col gap-2">
            <p className="text-[11px] text-on-surface-variant leading-relaxed">
              Importa un archivo XMI exportado desde Enterprise Architect (UML 2.1 / XMI 2.1 con diagramas). Las clases, estereotipos, visibilidades y relaciones serán leídas y validadas antes de modificar el canvas.
            </p>
            <div className="pt-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xmi,.xml,application/xml,text/xml"
                disabled={busy || !editable}
                onChange={previewFile}
                className="hidden"
              />
              <button
                type="button"
                disabled={busy || !editable}
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-6 px-4 border-2 border-dashed border-outline-variant/60 hover:border-secondary hover:bg-surface-container-high rounded-xl flex flex-col items-center justify-center gap-1.5 text-on-surface transition-all disabled:opacity-40"
              >
                <span className="material-symbols-outlined text-[28px] text-secondary">upload_file</span>
                <span className="font-semibold text-xs">Haz clic para seleccionar archivo XMI / XML</span>
                <span className="text-[10px] text-on-surface-variant">Archivos de hasta 4 MiB</span>
              </button>
            </div>
          </div>

          {busy && (
            <div className="p-3 bg-surface-container-high rounded text-center text-xs text-secondary font-mono animate-pulse">
              Analizando estructura XMI…
            </div>
          )}

          {/* Vista Previa de la Importación */}
          {preview && (
            <div className="bg-surface-container-lowest border border-secondary/40 rounded-xl p-3 shadow-md flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-secondary-fixed text-on-secondary-fixed rounded-full text-[10px] font-bold font-mono">
                    Vista Previa
                  </span>
                  <span className="font-bold text-on-surface text-xs">
                    {preview.summary.classes} clases • {preview.summary.relationships} relaciones • {preview.summary.attributes} atributos
                  </span>
                </div>
              </div>

              {preview.warnings?.length > 0 && (
                <div className="p-2 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg flex flex-col gap-1 text-[10px]">
                  <strong className="flex items-center gap-1 font-semibold">
                    <span className="material-symbols-outlined text-[14px]">warning</span>
                    Avisos de compatibilidad:
                  </strong>
                  <ul className="list-disc list-inside pl-1">
                    {preview.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Lista Detallada de Clases y Conexiones */}
              <div className="max-h-56 overflow-y-auto border border-outline-variant/30 rounded-lg p-2 flex flex-col gap-2 bg-surface-container-low/30 font-code-sm text-[11px]">
                {preview.document.nodes.map(node => (
                  <div key={node.id} className="p-1.5 bg-surface-container-lowest rounded border border-outline-variant/30">
                    <div className="font-bold text-on-surface flex items-center gap-1">
                      <span className="text-secondary">{node.data.package_name}.</span>
                      <span>{node.data.name}</span>
                      {node.data.is_abstract && <span className="text-on-surface-variant font-normal italic">(abstracta)</span>}
                    </div>
                    {node.data.attributes?.length > 0 && (
                      <div className="pl-2 pt-0.5 flex flex-wrap gap-1 text-[10px] text-on-surface-variant">
                        {node.data.attributes.map(a => (
                          <span key={a.name} className="bg-surface-container px-1 py-0.5 rounded">
                            {a.visibility} {a.name}: {a.type} {a.is_pk ? '(PK)' : ''}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {preview.document.edges.length > 0 && (
                  <div className="pt-1 border-t border-outline-variant/30 flex flex-col gap-1 text-[10px]">
                    <span className="font-bold text-on-surface-variant uppercase text-[9px]">Relaciones detectadas:</span>
                    {preview.document.edges.map(edge => {
                      const src = preview.document.nodes.find(n => n.id === edge.source)?.data.name || edge.source
                      const tgt = preview.document.nodes.find(n => n.id === edge.target)?.data.name || edge.target
                      return (
                        <div key={edge.id} className="text-on-surface-variant">
                          <strong className="text-secondary">{relations[edge.type] || edge.type}</strong>: {src} ({edge.source_cardinality}) → {tgt} ({edge.target_cardinality})
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Botones de Confirmación */}
              <div className="flex items-center justify-end gap-2 pt-1 border-t border-outline-variant/30">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setPreview(null)}
                  className="px-3 py-1.5 rounded-lg border border-outline-variant/60 hover:bg-surface-container text-on-surface font-medium text-xs transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={busy || !editable}
                  onClick={apply}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold flex items-center gap-1.5 shadow-sm hover:shadow-md transition-all text-xs disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]">check</span>
                  <span>Reemplazar Diagrama con esta Importación</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
