import { useEffect, useState } from 'react'
import { api } from '../api'
import { Editor } from '../uml/Editor'

const roleName = { OWNER: 'Propietario', EDITOR: 'Editor', VIEWER: 'Lector' }

export function Projects({ user, token, onExpired, onDirtyChange, onEditingChange }) {
  const [editing, setEditing] = useState(null)
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(null)
  const [members, setMembers] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    onEditingChange?.(Boolean(editing))
  }, [editing, onEditingChange])

  useEffect(() => {
    let active = true
    api(`/projects?offset=${offset}&limit=20`, { token }).then(data => {
      if (active) setProjects(data)
    }).catch(err => {
      if (active) {
        if (err.status === 401) onExpired()
        else setError(err.message)
      }
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, offset, revision, onExpired])

  async function action(operation) {
    setBusy(true)
    setError('')
    try {
      await operation()
    } catch (err) {
      if (err.status === 401) onExpired()
      else setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function open(id) {
    const project = await api(`/projects/${id}`, { token })
    const team = project.role === 'OWNER' ? await api(`/projects/${id}/members`, { token }) : []
    setSelected(project)
    setMembers(team)
  }

  function save(event) {
    event.preventDefault()
    const body = Object.fromEntries(new FormData(event.currentTarget))
    action(async () => {
      const project = await api(selected ? `/projects/${selected.id}` : '/projects', {
        token,
        method: selected ? 'PUT' : 'POST',
        body,
      })
      await open(project.id)
      setRevision(r => r + 1)
    })
  }

  function addMember(event) {
    event.preventDefault()
    const form = event.currentTarget
    const body = Object.fromEntries(new FormData(form))
    action(async () => {
      await api(`/projects/${selected.id}/members`, { token, method: 'PUT', body })
      await open(selected.id)
      form.reset()
    })
  }

  const readOnly = selected?.role === 'VIEWER'

  if (editing) {
    return (
      <Editor
        key={editing.id}
        project={editing}
        user={user}
        token={token}
        onClose={() => {
          setEditing(null)
          onEditingChange?.(false)
        }}
        onDirtyChange={onDirtyChange}
      />
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <div role="alert" className="p-3 bg-error-container text-on-error-container border-l-4 border-error rounded-lg text-xs flex items-center gap-2">
          <span className="material-symbols-outlined text-error text-[18px]">error</span>
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Columna Izquierda: Lista de Proyectos */}
        <div className="md:col-span-5 flex flex-col gap-4">
          <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-headline-md text-headline-md text-on-surface font-bold">
                  Mis Proyectos UML
                </h2>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  Proyectos propios y compartidos en tiempo real
                </p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => { setSelected(null); setMembers([]); setError('') }}
                className="px-3 py-1.5 bg-secondary hover:bg-secondary-container text-on-secondary text-xs font-semibold rounded-lg shadow-sm flex items-center gap-1 transition-all"
              >
                <span className="material-symbols-outlined text-[16px]">add</span>
                <span>Nuevo</span>
              </button>
            </div>

            {loading ? (
              <div className="py-8 text-center text-on-surface-variant font-code-sm text-xs">
                Cargando proyectos…
              </div>
            ) : projects.length === 0 ? (
              <div className="py-8 text-center text-on-surface-variant font-body-sm text-xs bg-surface-container-low rounded-lg p-4">
                No tienes proyectos aún. Crea uno nuevo para comenzar.
              </div>
            ) : (
              <div className="flex flex-col gap-2 max-h-[440px] overflow-y-auto pr-1">
                {projects.map(project => {
                  const isSelected = selected?.id === project.id
                  return (
                    <button
                      key={project.id}
                      type="button"
                      disabled={busy}
                      aria-pressed={isSelected}
                      onClick={() => action(() => open(project.id))}
                      className={`w-full p-3 rounded-lg border text-left transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-surface-container-high border-secondary ring-1 ring-secondary'
                          : 'bg-surface-container-low hover:bg-surface-container border-outline-variant/40'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="material-symbols-outlined text-secondary text-[20px]">
                          account_tree
                        </span>
                        <div className="truncate">
                          <span className="font-body-md text-xs font-semibold text-on-surface block truncate">
                            {project.name}
                          </span>
                          <span className="font-code-sm text-[10px] text-on-surface-variant">
                            ID: {project.id.slice(0, 8)}…
                          </span>
                        </div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium font-code-sm ${
                        project.role === 'OWNER'
                          ? 'bg-secondary-fixed text-on-secondary-fixed'
                          : project.role === 'EDITOR'
                          ? 'bg-surface-container-highest text-on-surface'
                          : 'bg-surface-container text-on-surface-variant'
                      }`}>
                        {roleName[project.role]}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}

            {/* Paginación */}
            <div className="flex items-center justify-between pt-4 mt-4 border-t border-outline-variant/40 text-xs">
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface-container-low hover:bg-surface-container text-on-surface disabled:opacity-40"
                disabled={offset === 0 || busy}
                onClick={() => setOffset(offset - 20)}
              >
                Anterior
              </button>
              <span className="font-code-sm text-on-surface-variant">
                Pág. {offset / 20 + 1}
              </span>
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface-container-low hover:bg-surface-container text-on-surface disabled:opacity-40"
                disabled={projects.length < 20 || busy}
                onClick={() => setOffset(offset + 20)}
              >
                Siguiente
              </button>
              <button
                type="button"
                className="px-2.5 py-1 rounded bg-surface-container-low hover:bg-surface-container text-on-surface"
                disabled={busy}
                onClick={() => setRevision(r => r + 1)}
                title="Actualizar lista"
              >
                <span className="material-symbols-outlined text-[14px]">refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Columna Derecha: Detalles del Proyecto y Colaboradores */}
        <div className="md:col-span-7 flex flex-col gap-5">
          {/* Card Detalles / Edición */}
          <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-outline-variant/40">
              <div>
                <h3 className="font-headline-md text-headline-md text-on-surface font-bold">
                  {selected ? 'Detalles del Proyecto' : 'Crear Nuevo Proyecto'}
                </h3>
                {selected && (
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Tu rol: <strong className="text-secondary">{roleName[selected.role]}</strong>
                  </span>
                )}
              </div>

              {selected && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => action(async () => {
                    const current = await api(`/projects/${selected.id}`, { token })
                    setEditing(current)
                  })}
                  className="px-4 py-2 bg-secondary hover:bg-secondary-container text-on-secondary font-semibold rounded-lg text-xs shadow-sm flex items-center gap-1.5 transition-all"
                >
                  <span className="material-symbols-outlined text-[18px]">schema</span>
                  <span>Abrir diagrama UML</span>
                </button>
              )}
            </div>

            <form
              key={selected ? `${selected.id}-${selected.updated_at}` : 'new'}
              onSubmit={save}
              className="flex flex-col gap-4"
            >
              <div className="flex flex-col gap-1">
                <label className="font-body-sm text-body-sm font-medium text-on-surface">
                  Nombre del proyecto
                </label>
                <input
                  name="name"
                  required
                  maxLength={150}
                  defaultValue={selected?.name || ''}
                  disabled={readOnly || busy}
                  placeholder="Ej. Taller Mecánico"
                  className="px-3 py-2 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary outline-none"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="font-body-sm text-body-sm font-medium text-on-surface">
                  Descripción
                </label>
                <textarea
                  name="description"
                  rows={3}
                  maxLength={5000}
                  defaultValue={selected?.description || ''}
                  disabled={readOnly || busy}
                  placeholder="Descripción de la arquitectura o modelo del dominio…"
                  className="px-3 py-2 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                {!readOnly && (
                  <button
                    type="submit"
                    disabled={busy}
                    className="px-4 py-2 bg-primary-container text-on-primary hover:bg-primary-container/90 font-medium rounded-lg text-xs transition-colors flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">save</span>
                    <span>{selected ? 'Guardar cambios' : 'Crear proyecto'}</span>
                  </button>
                )}

                {selected?.role === 'OWNER' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      if (window.confirm(`¿Eliminar el proyecto «${selected.name}» y su lienzo de clases?`)) {
                        action(async () => {
                          await api(`/projects/${selected.id}`, { token, method: 'DELETE' })
                          setSelected(null)
                          setMembers([])
                          setRevision(r => r + 1)
                        })
                      }
                    }}
                    className="px-3 py-1.5 bg-error-container hover:bg-error hover:text-on-error text-on-error-container font-medium rounded-lg text-xs transition-colors flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">delete</span>
                    <span>Eliminar proyecto</span>
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Card Colaboradores (solo para Propietarios) */}
          {selected?.role === 'OWNER' && (
            <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <span className="material-symbols-outlined text-secondary text-[20px]">group</span>
                <h3 className="font-headline-sm text-headline-sm text-on-surface font-bold">
                  Colaboradores del Proyecto
                </h3>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant mb-4">
                Invita colaboradores con cuenta registrada usando su correo electrónico.
              </p>

              <div className="flex flex-col gap-2 mb-5 divide-y divide-outline-variant/30">
                {members.map(member => (
                  <div key={member.user_id} className="pt-2 flex items-center justify-between">
                    <div>
                      <span className="font-body-md text-xs font-semibold text-on-surface block">
                        {member.full_name}
                      </span>
                      <span className="font-code-sm text-[11px] text-on-surface-variant">
                        {member.email} · <strong className="text-secondary">{roleName[member.role]}</strong>
                      </span>
                    </div>
                    {member.role !== 'OWNER' && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => action(async () => {
                          await api(`/projects/${selected.id}/members/${member.user_id}`, { token, method: 'DELETE' })
                          await open(selected.id)
                        })}
                        className="px-2.5 py-1 bg-surface-container-low hover:bg-error hover:text-on-error rounded text-xs text-on-surface-variant transition-colors flex items-center gap-1"
                        title="Retirar acceso"
                      >
                        <span className="material-symbols-outlined text-[14px]">person_remove</span>
                        <span>Retirar</span>
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* Formulario Añadir Colaborador */}
              <form onSubmit={addMember} className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-3 border-t border-outline-variant/40">
                <div className="sm:col-span-6">
                  <input
                    name="email"
                    type="email"
                    required
                    maxLength={255}
                    placeholder="correo@colaborador.com"
                    className="w-full px-3 py-1.5 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary outline-none"
                  />
                </div>
                <div className="sm:col-span-3">
                  <select
                    name="role"
                    className="w-full px-2 py-1.5 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary outline-none"
                  >
                    <option value="VIEWER">Lector</option>
                    <option value="EDITOR">Editor</option>
                  </select>
                </div>
                <div className="sm:col-span-3">
                  <button
                    type="submit"
                    disabled={busy}
                    className="w-full py-1.5 bg-secondary hover:bg-secondary-container text-on-secondary font-medium rounded-lg text-xs shadow-sm flex items-center justify-center gap-1 transition-all"
                  >
                    <span className="material-symbols-outlined text-[15px]">add</span>
                    <span>Invitar</span>
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
