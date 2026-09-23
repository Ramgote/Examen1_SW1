export function FooterStatus({
  selectedItemName,
  cursorPos = { x: 0, y: 0 },
  zoomLevel = 100,
  generatorReady = true,
}) {
  return (
    <footer className="fixed bottom-0 left-0 right-0 h-7 bg-surface-container-low border-t border-outline-variant/40 shadow-[0_-1px_4px_rgba(0,0,0,0.02)] z-50 flex items-center justify-between px-4 text-on-surface-variant font-code-sm text-code-sm select-none">
      <div className="flex items-center gap-3">
        <span>Cursor: X: {cursorPos.x}, Y: {cursorPos.y}</span>
        <span>•</span>
        <span className="truncate max-w-sm">
          {selectedItemName ? (
            <>
              Elemento seleccionado: <strong className="text-on-surface font-semibold">{selectedItemName}</strong>
            </>
          ) : (
            'Lienzo de Modelado UML 2.5'
          )}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span className={`font-semibold flex items-center gap-1 ${generatorReady ? 'text-secondary' : 'text-on-surface-variant'}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
          Spring Boot Generator: {generatorReady ? 'Preparado' : 'Pendiente'}
        </span>
        <span>•</span>
        <span>Zoom: {Math.round(zoomLevel)}%</span>
        <span className="material-symbols-outlined text-[14px] text-on-surface-variant" title="Cuadrícula activa">
          grid_view
        </span>
      </div>
    </footer>
  )
}
