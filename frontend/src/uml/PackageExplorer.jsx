import { useState } from 'react'

export function PackageExplorer({
  nodes = [],
  selectedId,
  onSelectNode,
  onAddClass,
  onAddSpecialClass,
  onSelectRelationType,
  relationType,
  disabled,
}) {
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState(true)

  // Agrupar clases por paquete
  const packages = nodes.reduce((acc, node) => {
    const pkg = node.data?.package_name || 'com.example.model'
    if (!acc[pkg]) acc[pkg] = []
    acc[pkg].push(node)
    return acc
  }, {})

  const filteredPackages = Object.entries(packages).reduce((acc, [pkg, items]) => {
    const matching = items.filter(n =>
      n.data.name.toLowerCase().includes(filter.toLowerCase()) ||
      pkg.toLowerCase().includes(filter.toLowerCase())
    )
    if (matching.length > 0 || !filter) acc[pkg] = matching
    return acc
  }, {})

  return (
    <aside className="w-72 bg-surface-container-lowest border-r border-outline-variant/60 flex flex-col h-full select-none z-30 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
      {/* Sección Superior: Explorador de Paquetes */}
      <div className="h-8 px-3 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40 flex-shrink-0">
        <span className="font-label-caps text-label-caps text-on-surface-variant tracking-wider">
          Explorador de Paquetes
        </span>
        <div className="flex items-center gap-1 text-on-surface-variant">
          <button
            type="button"
            className="hover:text-on-surface p-0.5 rounded"
            title="Filtrar clases"
            onClick={() => setFilter(f => (f ? '' : ' '))}
          >
            <span className="material-symbols-outlined text-[15px]">filter_alt</span>
          </button>
          <button
            type="button"
            className="hover:text-on-surface p-0.5 rounded"
            title="Alternar vista de árbol"
            onClick={() => setExpanded(e => !e)}
          >
            <span className="material-symbols-outlined text-[15px]">unfold_more</span>
          </button>
        </div>
      </div>

      {/* Input de filtro si está activo */}
      {filter !== '' && (
        <div className="p-2 border-b border-outline-variant/40 bg-surface-container-low">
          <input
            type="text"
            value={filter.trim()}
            onChange={e => setFilter(e.target.value)}
            placeholder="Buscar clase o paquete…"
            className="w-full px-2 py-1 bg-surface-container-lowest border border-outline-variant/60 rounded text-xs text-on-surface outline-none focus:ring-1 focus:ring-secondary"
            autoFocus
          />
        </div>
      )}

      {/* Árbol de Paquetes y Clases */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1 text-xs font-code-sm">
        {Object.keys(filteredPackages).length === 0 ? (
          <div className="p-4 text-center text-on-surface-variant font-body-sm text-xs">
            {nodes.length === 0 ? 'Sin clases en el modelo.' : 'No hay coincidencias.'}
          </div>
        ) : (
          Object.entries(filteredPackages).map(([pkgName, classList]) => (
            <div key={pkgName} className="flex flex-col gap-0.5">
              {/* Nodo de Paquete */}
              <div
                className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-high text-on-surface cursor-pointer"
                onClick={() => setExpanded(e => !e)}
              >
                <span className="material-symbols-outlined text-[16px] text-secondary">
                  {expanded ? 'folder_open' : 'folder'}
                </span>
                <span className="font-code-sm font-semibold truncate text-[#0051d5]">
                  {pkgName}
                </span>
              </div>

              {/* Lista de Clases del Paquete */}
              {expanded && (
                <div className="pl-5 flex flex-col gap-0.5 border-l border-outline-variant/30 ml-3">
                  {classList.map(node => {
                    const isSelected = selectedId === node.id
                    const isAbstract = node.data?.is_abstract
                    return (
                      <div
                        key={node.id}
                        onClick={() => onSelectNode(node.id)}
                        className={`flex items-center justify-between gap-1.5 px-2 py-1 rounded cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-surface-container-high text-on-surface font-semibold ring-1 ring-secondary'
                            : 'hover:bg-surface-container-low text-on-surface'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <span className="material-symbols-outlined text-[15px] text-secondary">
                            {isAbstract ? 'category' : 'class'}
                          </span>
                          <span className={`truncate ${isAbstract ? 'italic text-on-surface-variant' : ''}`}>
                            {node.data.name}
                          </span>
                        </div>
                        {node.data.attributes?.some(a => a.is_pk) && (
                          <span className="text-[9px] px-1 bg-secondary-fixed text-on-secondary-fixed rounded font-bold">
                            PK
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Sección Inferior: Caja de Herramientas UML (Elementos y Relaciones) */}
      <div className="mt-auto border-t border-outline-variant/60 flex-shrink-0 bg-surface-container-lowest flex flex-col max-h-[50%] overflow-y-auto">
        {/* Cabecera Elementos de Clase */}
        <div className="h-7 px-3 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40 flex-shrink-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant font-bold uppercase tracking-wider">
            Elementos de Clase
          </span>
          <span className="material-symbols-outlined text-[15px] text-on-surface-variant">
            category
          </span>
        </div>

        <div className="p-1.5 grid grid-cols-2 gap-1 bg-surface-container-lowest">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onAddClass?.()}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-left border border-outline-variant/30 transition-colors disabled:opacity-40"
            title="Añadir nueva clase UML estándar"
          >
            <span className="material-symbols-outlined text-[15px] text-secondary">rectangle</span>
            <span className="font-body-sm text-[11px] text-on-surface">Clase</span>
          </button>

          <button
            type="button"
            disabled={disabled}
            onClick={() => onAddSpecialClass?.('interface')}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-left border border-outline-variant/30 transition-colors disabled:opacity-40"
            title="Añadir Interfaz UML «interface»"
          >
            <span className="material-symbols-outlined text-[15px] text-secondary">check_box_outline_blank</span>
            <span className="font-body-sm text-[11px] text-on-surface">Interfaz</span>
          </button>

          <button
            type="button"
            disabled={disabled}
            onClick={() => onAddSpecialClass?.('abstract')}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-left border border-outline-variant/30 transition-colors disabled:opacity-40"
            title="Añadir Clase Abstracta «abstract»"
          >
            <span className="material-symbols-outlined text-[15px] text-secondary">category</span>
            <span className="font-body-sm text-[11px] text-on-surface">Abstracta</span>
          </button>

          <button
            type="button"
            disabled={disabled}
            onClick={() => onAddSpecialClass?.('enum')}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-left border border-outline-variant/30 transition-colors disabled:opacity-40"
            title="Añadir Enumeración UML «enumeration»"
          >
            <span className="material-symbols-outlined text-[15px] text-secondary">list</span>
            <span className="font-body-sm text-[11px] text-on-surface">Enum</span>
          </button>
        </div>

        {/* Cabecera Class Relationships (Enterprise Architect style) */}
        <div className="h-7 px-3 bg-surface-container-low flex items-center justify-between border-t border-b border-outline-variant/40 flex-shrink-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant font-bold uppercase tracking-wider flex items-center gap-1">
            <span className="material-symbols-outlined text-[13px] text-secondary">share</span>
            Class Relationships
          </span>
          <span className="text-[10px] text-secondary font-mono">UML 2.5</span>
        </div>

        {/* Lista de Relaciones */}
        <div className="p-1.5 flex flex-col gap-0.5 bg-surface-container-lowest">
          {/* 1. Associate */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('association')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'association'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Associate: Relación de asociación estándar entre clases"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="3" y1="15" x2="14" y2="4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M8 3 L15 3 L15 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
            <span className="font-body-sm text-[11px]">Associate</span>
          </button>

          {/* 2. Generalize */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('generalization')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'generalization'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Generalize: Relación de herencia / especialización"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="3" y1="15" x2="11" y2="7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <polygon points="9,3 16,5 14,12" fill="white" stroke="currentColor" strokeWidth="1.6" />
            </svg>
            <span className="font-body-sm text-[11px]">Generalize</span>
          </button>

          {/* 3. Compose */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('composition')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'composition'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Compose: Composición fuerte (el ciclo de vida del hijo depende del padre)"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="8" y1="10" x2="15" y2="3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <polygon points="2,14 6,10 10,14 6,18" fill="currentColor" stroke="currentColor" strokeWidth="1" />
            </svg>
            <span className="font-body-sm text-[11px]">Compose</span>
          </button>

          {/* 4. Aggregate */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('aggregation')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'aggregation'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Aggregate: Agregación compartida (el objeto parte puede existir sin el todo)"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="8" y1="10" x2="15" y2="3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <polygon points="2,14 6,10 10,14 6,18" fill="white" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <span className="font-body-sm text-[11px]">Aggregate</span>
          </button>

          {/* 5. Association Class */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('association_class')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'association_class'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Association Class: Asociación con clase intermedia vinculada"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="2" y1="14" x2="15" y2="3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <line x1="8" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="1.2" strokeDasharray="1.5 1.5" />
              <rect x="11" y="11" width="5" height="5" fill="white" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            <span className="font-body-sm text-[11px]">Association Class</span>
          </button>

          {/* 6. Realize */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('realization')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'realization'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Realize: Implementación o realización de interfaces"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="3" y1="15" x2="11" y2="7" stroke="currentColor" strokeWidth="1.8" strokeDasharray="2.5 2" />
              <polygon points="9,3 16,5 14,12" fill="white" stroke="currentColor" strokeWidth="1.6" />
            </svg>
            <span className="font-body-sm text-[11px]">Realize</span>
          </button>

          {/* 7. Template Binding */}
          <button
            type="button"
            onClick={() => onSelectRelationType?.('template_binding')}
            className={`flex items-center gap-2 px-2 py-1 rounded text-left border transition-all ${
              relationType === 'template_binding'
                ? 'bg-secondary-fixed/30 border-secondary text-[#0051d5] font-semibold shadow-xs'
                : 'hover:bg-surface-container-low border-transparent text-on-surface'
            }`}
            title="Template Binding: Vinculación con parámetros genéricos «bind»"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-secondary shrink-0">
              <line x1="3" y1="15" x2="13" y2="5" stroke="currentColor" strokeWidth="1.8" strokeDasharray="2.5 2" />
              <path d="M8 4 L14 4 L14 10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              <line x1="6" y1="9" x2="10" y2="13" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            <span className="font-body-sm text-[11px]">Template Binding</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
