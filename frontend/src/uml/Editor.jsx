import { useEffect, useRef, useState } from 'react'
import { ReactFlow, Background, MiniMap, applyNodeChanges } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useCollaboration } from './useCollaboration'
import { ClassNode } from './ClassNode'
import { RelationEdge } from './RelationEdge'
import { Inspector } from './Inspector'
import { PackageExplorer } from './PackageExplorer'
import { CanvasHud } from './CanvasHud'
import { LegacyRefModal } from './LegacyRefModal'
import { FooterStatus } from './FooterStatus'
import { TopHeader } from './TopHeader'
import { XmiPanel } from './XmiPanel'
import { GenerationPanel } from './GenerationPanel'
import { AssistantPanel } from './AssistantPanel'
import { newAssociationClass, newClass, newRelation, relations, removeClass, serializeDiagram } from './document'
import { reloadDraft } from './saveStatus'
import { arrangeReserved } from './layout'
import './editor.css'

const nodeTypes = { uml_class: ClassNode }
const edgeTypes = { uml_relation: RelationEdge }

export function Editor({ project, user, token, onClose, onDirtyChange }) {
  const shared = useCollaboration(project, token)
  const { diagram, dirty, error, change, save } = shared
  const [selection, setSelection] = useState(null)
  const [relationType, setRelationType] = useState('association')
  const [measurements, setMeasurements] = useState({})
  const [exchangeBusy, setExchangeBusy] = useState(false)
  const [assistantBusy, setAssistantBusy] = useState(false)
  const [activeTab, setActiveTab] = useState('diagram')
  const [showXmiModal, setShowXmiModal] = useState(false)
  const [showGenModal, setShowGenModal] = useState(false)
  const [showAssistantDock, setShowAssistantDock] = useState(false)
  const [assistantOpened, setAssistantOpened] = useState(false)
  const [showLegacyModal, setShowLegacyModal] = useState(false)
  const [activeHudMode, setActiveHudMode] = useState('select')
  const [snapGrid, setSnapGrid] = useState(16)
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 })
  const [zoomLevel, setZoomLevel] = useState(100)
  const [layoutBusy, setLayoutBusy] = useState(false)
  const [reservationBusy, setReservationBusy] = useState(false)

  const busy = exchangeBusy || assistantBusy
  const instance = useRef(null)
  const readOnly = shared.role === 'VIEWER'
  // Validation failures must still allow correcting the local draft.
  const disabled = readOnly || !diagram || busy || !shared.ready
  const reservations = shared.reservations || []
  const owns = id => reservations.some(r => r.node_id === id && r.connection_id === shared.connectionId)
  const foreign = id => reservations.find(r => r.node_id === id && r.connection_id !== shared.connectionId)

  function selectItem(item) {
    setSelection(item)
  }

  function reload() {
    if (busy) return
    if (reloadDraft(shared, message => window.confirm(message))) setSelection(null)
  }

  function downloadDraft() {
    if (!diagram) return
    const document = serializeDiagram(diagram, instance.current?.getViewport())
    const url = URL.createObjectURL(new Blob([JSON.stringify(document, null, 2)], { type: 'application/json' }))
    const anchor = window.document.createElement('a')
    anchor.href = url
    anchor.download = `borrador-${project.id}-v${diagram.version}.json`
    window.document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  useEffect(() => {
    onDirtyChange(dirty)
    const warn = event => { if (dirty) { event.preventDefault(); event.returnValue = '' } }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, onDirtyChange])

  function back() {
    if (assistantBusy) return
    if (dirty && !window.confirm('Hay cambios sin guardar. ¿Salir del editor y descartarlos?')) return
    onDirtyChange(false)
    onClose()
  }

  async function addRelation(source, target, sourceHandle, targetHandle) {
    if (disabled || !await shared.reserve([source, target])) return
    if (relationType === 'association_class') {
      if (diagram.nodes.length >= 200) return
      const sourceNode = diagram.nodes.find(n => n.id === source)
      const targetNode = diagram.nodes.find(n => n.id === target)
      const assocClass = newAssociationClass(diagram.nodes, sourceNode, targetNode)
      if (!await shared.reserve([assocClass.id])) return

      const edge = {
        ...newRelation(source, target, relationType),
        relation_name: assocClass.data.name,
        association_node_id: assocClass.id,
        source_handle: sourceHandle,
        target_handle: targetHandle,
        source_cardinality: '1..*',
        target_cardinality: '1..*'
      }

      change(previous => ({
        ...previous,
        nodes: [...previous.nodes, assocClass],
        edges: [...previous.edges, edge]
      }))
      setSelection({ kind: 'node', id: assocClass.id })
      return
    }
    const edge = { ...newRelation(source, target, relationType), source_handle: sourceHandle, target_handle: targetHandle }
    change(previous => ({ ...previous, edges: [...previous.edges, edge] }))
    setSelection({ kind: 'edge', id: edge.id })
  }

  async function handleAddClass(specialType) {
    if (disabled || !diagram || diagram.nodes.length >= 200) return
    const added = newClass(diagram.nodes, specialType === 'enum' ? 'enumeration' : specialType === 'interface' ? 'interface' : 'class')
    if (specialType === 'abstract') {
      added.data.is_abstract = true

    }
    if (!await shared.reserve([added.id])) return
    change(previous => ({ ...previous, nodes: [...previous.nodes, added] }))
    setSelection({ kind: 'node', id: added.id })
  }

  async function handleAutoLayout() {
    if (disabled || layoutBusy || !diagram?.nodes.length) return
    setLayoutBusy(true)
    try {
      if (!await arrangeReserved(shared)) return
      setTimeout(() => instance.current?.fitView({ padding: 0.2 }), 50)
    } finally {
      setLayoutBusy(false)
    }
  }

  const node = diagram?.nodes.find(item => selection?.kind === 'node' && item.id === selection.id)
  const edge = diagram?.edges.find(item => selection?.kind === 'edge' && item.id === selection.id)
  const selectedItemName = node ? `Clase <${node.data.name}>` : edge ? `Relación <${relations[edge.type] || edge.type}>` : null

  return (
    <section className="uml-editor-workbench fixed inset-0 z-40 bg-surface flex flex-col select-none overflow-hidden font-sans">
      {/* Header Superior de Doble Nivel */}
      <TopHeader
        project={project}
        user={user}
        diagram={diagram}
        dirty={dirty}
        shared={shared}
        disabled={disabled}
        busy={busy}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onSaveAndRelease={() => { shared.finish(); setSelection(null) }}
        onSync={save}
        onOpenXmi={() => { setActiveTab('xmi'); setShowXmiModal(true) }}
        onOpenGeneration={() => { setActiveTab('generation'); setShowGenModal(true) }}
        onOpenAssistant={() => { setActiveTab('assistant'); setAssistantOpened(true); setShowAssistantDock(true) }}
        onBack={back}
      />

      {/* Área Principal de 3 Paneles (debajo de Header de 80px y arriba de Footer de 28px) */}
      <div className="pt-20 pb-7 flex-1 flex w-full h-full overflow-hidden relative">
        {/* Panel Lateral Izquierdo: Explorador de Paquetes + Caja de Herramientas UML */}
        <PackageExplorer
          nodes={diagram?.nodes || []}
          selectedId={node?.id}
          onSelectNode={id => selectItem({ kind: 'node', id })}
          onAddClass={() => handleAddClass()}
          onAddSpecialClass={type => handleAddClass(type)}
          onSelectRelationType={setRelationType}
          relationType={relationType}
          disabled={disabled}
        />

        {/* Panel Central: Lienzo UML (Canvas) */}
        <div
          className="flex-1 h-full relative overflow-hidden bg-surface"
          aria-label="Lienzo de clases UML"
          onMouseMove={e => {
            const bounds = e.currentTarget.getBoundingClientRect()
            setCursorPos({ x: Math.round(e.clientX - bounds.left), y: Math.round(e.clientY - bounds.top) })
          }}
        >
          {/* HUD Superior Flotante */}
          <CanvasHud
            activeMode={activeHudMode}
            setActiveMode={setActiveHudMode}
            onAutoLayout={handleAutoLayout}
            layoutDisabled={disabled || layoutBusy || !diagram?.nodes.length}
            snapGrid={snapGrid}
            onToggleSnap={() => setSnapGrid(s => (s ? 0 : 16))}
            onOpenLegacyRef={() => setShowLegacyModal(true)}
            onZoomIn={() => instance.current?.zoomIn()}
            onZoomOut={() => instance.current?.zoomOut()}
            onZoomFit={() => instance.current?.fitView({ padding: 0.15 })}
            zoomLevel={zoomLevel}
          />

          {(error || shared.blocked || dirty) && (
            <div role={error || shared.blocked ? 'alert' : 'status'} className={`absolute top-14 left-4 right-4 z-30 p-2.5 border-l-4 rounded shadow-md text-xs font-mono flex flex-wrap gap-2 items-center justify-between ${error || shared.blocked ? 'bg-error-container text-on-error-container border-error' : 'bg-surface-container text-on-surface border-secondary'}`}>
              <span>{error || (shared.blocked ? 'La sincronización está bloqueada. Conserva tu borrador antes de recargar.' : 'Hay cambios pendientes de confirmación del servidor.')}</span>
              <div className="flex items-center gap-3 shrink-0 ml-3">
                <button type="button" onClick={downloadDraft} disabled={!diagram} className="underline font-bold text-xs disabled:opacity-40">Descargar borrador JSON</button>
                <button type="button" onClick={reload} disabled={busy || !shared.ready || shared.pending || !diagram} className="underline font-bold text-xs disabled:opacity-40" title="Cargar la última versión recibida del servidor">Recargar</button>
              </div>
            </div>
          )}

          {diagram && (
            <ReactFlow
              nodes={diagram.nodes.map(n => ({
                ...n,
                draggable: !disabled && owns(n.id) && activeHudMode !== 'pan',
                connectable: !disabled && !foreign(n.id),
                data: { ...n.data, canResize: !disabled && owns(n.id), reservationLabel: reservations.find(r => r.node_id === n.id)?.name },
                measured: measurements[n.id],
                selected: selection?.kind === 'node' && selection.id === n.id,
              }))}
              edges={diagram.edges.map(e => ({
                id: e.id,
                source: e.source,
                target: e.target,
                sourceHandle: e.source_handle,
                targetHandle: e.target_handle,
                type: 'uml_relation',
                data: e,
                selected: selection?.kind === 'edge' && selection.id === e.id,
              }))}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              nodesDraggable={!disabled && activeHudMode !== 'pan'}
              nodesConnectable={!disabled}
              edgesReconnectable={false}
              deleteKeyCode={null}
              minZoom={0.1}
              maxZoom={4}
              snapToGrid={!!snapGrid}
              snapGrid={snapGrid ? [snapGrid, snapGrid] : undefined}
              panOnDrag={activeHudMode === 'pan'}
              defaultViewport={diagram.metadata.viewport || { x: 0, y: 0, zoom: 1 }}
              fitView={!diagram.metadata.viewport}
              onInit={flow => {
                instance.current = flow
                setZoomLevel((flow.getZoom() || 1) * 100)
              }}
              onMove={(_, vp) => {
                if (vp?.zoom) setZoomLevel(vp.zoom * 100)
              }}
              onMoveEnd={(_, viewport) => {
                if (!disabled) change(previous => ({ ...previous, metadata: { ...previous.metadata, viewport } }))
              }}
              onNodesChange={changes => {
                const dimensions = changes.filter(c => c.type === 'dimensions' && c.dimensions)
                if (dimensions.length) {
                  setMeasurements(previous => ({ ...previous, ...Object.fromEntries(dimensions.map(c => [c.id, c.dimensions])) }))
                }
                const positions = changes.filter(c => !disabled && owns(c.id) && (c.type === 'position' || (c.type === 'dimensions' && c.setAttributes)))
                if (positions.length) {
                  change(previous => ({ ...previous, nodes: applyNodeChanges(positions, previous.nodes) }))
                }
              }}
              onNodeClick={(_, n) => selectItem({ kind: 'node', id: n.id })}
              onEdgeClick={(_, e) => selectItem({ kind: 'edge', id: e.id })}
              onPaneClick={() => setSelection(null)}
              onConnect={({ source, target, sourceHandle, targetHandle }) => {
                if (!disabled && diagram.edges.length < 500) addRelation(source, target, sourceHandle, targetHandle)
              }}
            >
              <Background gap={20} color="#cbd5e1" />
              <MiniMap pannable zoomable />
            </ReactFlow>
          )}

          {/* Modal / Dialogo de Comparación Arquitectural */}
          <LegacyRefModal
            isOpen={showLegacyModal}
            onClose={() => setShowLegacyModal(false)}
          />

          {/* Modal / Dialogo de Intercambio XMI */}
          {showXmiModal && (
            <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden border border-outline-variant/60">
                <div className="h-10 px-4 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40">
                  <div className="flex items-center gap-2 font-semibold text-on-surface">
                    <span className="material-symbols-outlined text-secondary text-[18px]">sync_alt</span>
                    <span>Intercambio XMI (Enterprise Architect 17.0 / 15.0)</span>
                  </div>
                  <button
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container text-on-surface-variant"
                    type="button"
                    onClick={() => { setShowXmiModal(false); if (activeTab === 'xmi') setActiveTab('diagram') }}
                  >
                    <span className="material-symbols-outlined text-[18px]">close</span>
                  </button>
                </div>
                <div className="p-4 overflow-y-auto">
                  <XmiPanel projectId={project.id} token={token} shared={shared} onBusy={setExchangeBusy} externalBusy={assistantBusy} />
                </div>
              </div>
            </div>
          )}

          {/* Modal / Dialogo de Generación Spring Boot */}
          {showGenModal && (
            <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden border border-outline-variant/60">
                <div className="h-10 px-4 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40">
                  <div className="flex items-center gap-2 font-semibold text-on-surface">
                    <span className="material-symbols-outlined text-secondary text-[18px]">bolt</span>
                    <span>Generación de Spring Boot y Flutter</span>
                  </div>
                  <button
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container text-on-surface-variant"
                    type="button"
                    onClick={() => { setShowGenModal(false); if (activeTab === 'generation') setActiveTab('diagram') }}
                  >
                    <span className="material-symbols-outlined text-[18px]">close</span>
                  </button>
                </div>
                <div className="p-4 overflow-y-auto">
                  <GenerationPanel projectId={project.id} token={token} shared={shared} exchangeBusy={busy} />
                </div>
              </div>
            </div>
          )}

          {/* Dock Asistente IA Multimodal (Bottom Drawer CASE Studio) */}
          {assistantOpened && (
            <div
              hidden={!showAssistantDock && !assistantBusy}
              style={!showAssistantDock && !assistantBusy ? { display: 'none' } : undefined}
              className="absolute bottom-2 left-3 right-3 z-30 bg-surface-container-lowest/95 backdrop-blur-md border border-outline-variant/60 shadow-2xl rounded-xl flex flex-col overflow-hidden max-h-[65vh]"
            >
              {/* Cabecera del Drawer */}
              <div
                className="h-10 px-3.5 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40 flex-shrink-0 select-none"
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary text-[18px]">auto_awesome</span>
                  <span className="font-headline-sm text-xs font-bold text-on-surface">
                    Asistente IA Multimodal Gemini
                  </span>
                  <span className="px-2 py-0.5 bg-secondary-fixed text-on-secondary-fixed rounded-full text-[9px] font-bold font-mono">
                    PRO 1.5
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={assistantBusy}
                    onClick={e => {
                      e.stopPropagation()
                      if (assistantBusy) return
                      setShowAssistantDock(false)
                      if (activeTab === 'assistant') setActiveTab('diagram')
                    }}
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container text-on-surface-variant hover:text-error transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    title={assistantBusy ? 'Espera a que termine la tarea del asistente' : 'Cerrar panel de asistente'}
                  >
                    <span className="material-symbols-outlined text-[16px]">close</span>
                  </button>
                </div>
              </div>

              {/* Cuerpo del Drawer */}
                <div className="p-3.5 overflow-y-auto flex-1 bg-surface-container-lowest">
                  <AssistantPanel
                    key={project.id}
                    visible={showAssistantDock || assistantBusy}
                    projectId={project.id}
                    token={token}
                    shared={shared}
                    externalBusy={exchangeBusy}
                    onBusy={setAssistantBusy}
                  />
                </div>
            </div>
          )}
        </div>

        {/* Panel Lateral Derecho: Inspector de Propiedades + Colaboración en Vivo */}
        <Inspector
          node={node}
          edge={edge}
          nodes={diagram?.nodes || []}
          editing={node ? owns(node.id) : edge ? owns(edge.source) && owns(edge.target) : false}
          editUnavailable={disabled || reservationBusy || (node ? !!foreign(node.id) : edge ? !!foreign(edge.source) || !!foreign(edge.target) : true)}
          onStartEditing={async () => {
            if (disabled || reservationBusy || (!node && !edge)) return
            setReservationBusy(true)
            try {
              await shared.reserve(node ? [node.id] : [...new Set([edge.source, edge.target])])
            } finally {
              setReservationBusy(false)
            }
          }}
          disabled={disabled || (node ? !owns(node.id) : edge ? !owns(edge.source) || !owns(edge.target) : true)}
          updateNode={data => change(previous => ({ ...previous, nodes: previous.nodes.map(n => (n.id === node.id ? { ...n, data } : n)) }))}
          updateEdge={async data => {
            let added = null
            if (data.type === 'association_class' && !data.association_node_id) {
              if (diagram.nodes.length >= 200) return
              added = newAssociationClass(diagram.nodes, diagram.nodes.find(n => n.id === data.source), diagram.nodes.find(n => n.id === data.target))
              data = { ...data, association_node_id: added.id }
            } else if (data.type !== 'association_class') {
              data = { ...data, association_node_id: null }
            }
            if (!await shared.reserve([...new Set([edge.source, edge.target, edge.association_node_id, data.source, data.target, data.association_node_id].filter(Boolean))])) return
            change(previous => ({ ...previous, nodes: added ? [...previous.nodes, added] : previous.nodes, edges: previous.edges.map(e => (e.id === edge.id ? data : e)) }))
          }}
          onDelete={async () => {
            if (!window.confirm(node ? '¿Eliminar la clase y todas sus relaciones?' : '¿Eliminar esta relación?')) return
            const ids = node ? [node.id, ...diagram.edges.filter(e => e.source === node.id || e.target === node.id || e.association_node_id === node.id).flatMap(e => [e.source, e.target, e.association_node_id].filter(Boolean))] : [edge.source, edge.target, edge.association_node_id].filter(Boolean)
            if (!await shared.reserve([...new Set(ids)])) return
            change(previous => (node ? removeClass(previous, node.id) : { ...previous, edges: previous.edges.filter(e => e.id !== edge.id) }))
            setSelection(null)
          }}
          shared={shared}
        />
      </div>

      {/* Barra de Estado Inferior (Footer 28px) */}
      <FooterStatus
        selectedItemName={selectedItemName}
        cursorPos={cursorPos}
        zoomLevel={zoomLevel}
        generatorReady={!dirty && shared.ready && !shared.pending}
      />
    </section>
  )
}
