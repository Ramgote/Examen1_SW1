import { saveStatus } from './saveStatus'

export function TopHeader({
  project,
  user,
  diagram,
  dirty,
  shared,
  disabled,
  busy,
  activeTab,
  setActiveTab,
  onSaveAndRelease,
  onSync,
  onOpenXmi,
  onOpenGeneration,
  onOpenAssistant,
  onBack,
}) {
  const readOnly = shared.role === 'VIEWER'
  const reservations = shared.reservations || []
  const hasMyReservations = reservations.some(r => r.connection_id === shared.connectionId)
  const sync = saveStatus({ ...shared, diagram, dirty })

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-primary-container text-on-primary select-none shadow-sm">
      <div className="w-full flex flex-col">
        {/* Nivel 1: Barra de Estado de la Aplicación y Proyecto */}
        <div className="h-9 px-4 flex items-center justify-between bg-primary-container text-on-primary text-xs border-b border-inverse-surface/40">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-secondary-fixed text-[18px]">account_tree</span>
            <span className="font-code-sm text-code-sm text-surface-variant font-semibold tracking-wide truncate max-w-md">
              UML Studio - [{project.name}.eapx{dirty ? '*' : ''}]
            </span>
            <span role="status" aria-live="polite" className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium ${
              sync.kind === 'saved' ? 'bg-secondary text-on-secondary' : ['error', 'offline'].includes(sync.kind) ? 'bg-error text-on-error' : 'bg-secondary-container text-on-secondary-container'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full bg-current ${sync.kind === 'syncing' ? 'animate-pulse' : ''}`}></span>
              {sync.label}
            </span>
            {dirty && !shared.pending && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface text-[10px] font-code-sm">
                ● Borrador local
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface font-code-sm text-[11px]">
              <span className="w-2 h-2 rounded-full bg-secondary"></span>
              {shared.participants.length} {shared.participants.length === 1 ? 'activo' : 'activos'} • {user?.full_name || 'Tú'} ({readOnly ? 'Lector' : 'Tú'})
            </div>
            <div className="flex items-center gap-0.5 text-on-primary-container">
              <button
                className="w-6 h-6 flex items-center justify-center rounded hover:bg-error hover:text-on-error transition-colors text-on-primary-container"
                type="button"
                title="Salir del editor"
                disabled={busy}
                onClick={onBack}
              >
                <span className="material-symbols-outlined text-[15px]">close</span>
              </button>
            </div>
            <div
              className="w-7 h-7 rounded-full bg-secondary text-on-secondary flex items-center justify-center font-bold text-xs shadow-sm"
              title={user?.full_name ? `${user.full_name} (${user.email || ''})` : 'Usuario'}
            >
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <span className="material-symbols-outlined text-[16px]">person</span>}
            </div>
          </div>
        </div>

        {/* Nivel 2: Barra de Pestañas de Navegación y Acciones Rápidas */}
        <div className="h-11 px-4 flex items-center justify-between bg-surface-container-lowest text-on-surface border-b border-outline-variant/50 shadow-[0_1px_4px_rgba(0,0,0,0.05)]">
          {/* Pestañas de Navegación */}
          <nav className="flex items-center gap-1 h-full">
            <button
              type="button"
              className="px-3 py-1 rounded transition-colors text-xs font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low flex items-center gap-1"
              onClick={onBack}
              disabled={busy}
              title="Volver a la lista de proyectos"
            >
              <span className="material-symbols-outlined text-[15px]">home</span>
              <span>Inicio</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded transition-colors text-xs font-semibold flex items-center gap-1 ${
                activeTab === 'diagram' ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
              }`}
              onClick={() => setActiveTab('diagram')}
            >
              <span className="material-symbols-outlined text-[15px] text-secondary">schema</span>
              <span>Diagrama</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded transition-colors text-xs font-medium flex items-center gap-1 ${
                activeTab === 'modeling' ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
              }`}
              onClick={() => setActiveTab(activeTab === 'modeling' ? 'diagram' : 'modeling')}
            >
              <span className="material-symbols-outlined text-[15px]">category</span>
              <span>Modelado</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded transition-colors text-xs font-medium flex items-center gap-1 ${
                activeTab === 'xmi' ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
              }`}
              onClick={onOpenXmi}
            >
              <span className="material-symbols-outlined text-[15px]">sync_alt</span>
              <span>Intercambio XMI</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded transition-colors text-xs font-medium flex items-center gap-1 ${
                activeTab === 'generation' ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
              }`}
              onClick={onOpenGeneration}
            >
              <span className="material-symbols-outlined text-[15px]">code_blocks</span>
              <span>Generación Código</span>
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded transition-colors text-xs font-medium flex items-center gap-1 ${
                activeTab === 'assistant' ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
              }`}
              onClick={onOpenAssistant}
            >
              <span className="material-symbols-outlined text-[15px] text-secondary">smart_toy</span>
              <span>Asistente IA</span>
            </button>
          </nav>

          {/* Botones de Acción Rápida */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              className="flex items-center gap-1 px-3 py-1 bg-surface-container-low hover:bg-surface-container-high text-on-surface border border-outline-variant/60 rounded transition-colors text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={disabled || shared.blocked || shared.pending || !hasMyReservations}
              onClick={onSaveAndRelease}
              title="Guardar cambios locales y liberar reservas exclusivas de clases (RF-27)"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">lock_open</span>
              <span>Guardar &amp; Liberar</span>
            </button>

            <button
              type="button"
              className="flex items-center gap-1 px-3 py-1 bg-surface-container-low hover:bg-surface-container-high text-on-surface border border-outline-variant/60 rounded transition-colors text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={!diagram || disabled || !dirty || !shared.ready || shared.pending || shared.blocked}
              onClick={onSync}
              title="Enviar borrador local pendiente al servidor colaborativo"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">sync</span>
              <span>Sincronizar</span>
            </button>

            <button
              type="button"
              className="flex items-center gap-1 px-3 py-1 bg-surface-container-low hover:bg-surface-container-high text-on-surface border border-outline-variant/60 rounded transition-colors text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={busy}
              onClick={onOpenXmi}
              title="Exportar modelo UML a Enterprise Architect XMI"
            >
              <span className="material-symbols-outlined text-[16px]">file_upload</span>
              <span>Exportar XMI</span>
            </button>

            <button
              type="button"
              className="flex items-center gap-1 px-3 py-1 bg-surface-container-low hover:bg-surface-container-high text-on-surface border border-outline-variant/60 rounded transition-colors text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={busy || readOnly}
              onClick={onOpenXmi}
              title="Importar modelo XMI desde Enterprise Architect"
            >
              <span className="material-symbols-outlined text-[16px]">file_download</span>
              <span>Importar XMI</span>
            </button>

            <button
              type="button"
              className="flex items-center gap-1.5 px-3.5 py-1 bg-secondary hover:bg-secondary-container text-on-secondary font-medium rounded transition-colors text-xs shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={busy}
              onClick={onOpenGeneration}
              title="Generar Spring Boot y app Flutter Android"
            >
              <span className="material-symbols-outlined text-[16px] text-on-secondary">bolt</span>
              <span className="font-semibold">Generar proyecto</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
