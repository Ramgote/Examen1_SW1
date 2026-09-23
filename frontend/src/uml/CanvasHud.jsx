export function CanvasHud({
  activeMode = 'select',
  setActiveMode,
  onAutoLayout,
  layoutDisabled,
  snapGrid = 16,
  onToggleSnap,
  onOpenLegacyRef,
  onZoomIn,
  onZoomOut,
  onZoomFit,
  zoomLevel = 100,
}) {
  return (
    <>
      {/* HUD Superior Flotante */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 p-1 bg-surface-container-lowest/95 backdrop-blur shadow-md rounded-xl border border-outline-variant/60 select-none">
        {/* Modos de Puntero */}
        <div className="flex items-center bg-surface-container-low p-0.5 rounded-lg">
          <button
            type="button"
            onClick={() => setActiveMode?.('select')}
            className={`w-7 h-7 flex items-center justify-center rounded transition-all ${
              activeMode === 'select'
                ? 'bg-secondary text-on-secondary shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
            title="Seleccionar elemento (V)"
          >
            <span className="material-symbols-outlined text-[16px]">near_me</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode?.('pan')}
            className={`w-7 h-7 flex items-center justify-center rounded transition-all ${
              activeMode === 'pan'
                ? 'bg-secondary text-on-secondary shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
            title="Mano / Mover Lienzo (H)"
          >
            <span className="material-symbols-outlined text-[16px]">pan_tool</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode?.('connector')}
            className={`w-7 h-7 flex items-center justify-center rounded transition-all ${
              activeMode === 'connector'
                ? 'bg-secondary text-on-secondary shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
            title="Enlace de Asociación (C)"
          >
            <span className="material-symbols-outlined text-[16px]">timeline</span>
          </button>
        </div>

        <div className="w-px h-5 bg-outline-variant/50 mx-0.5"></div>

        <button
          type="button"
          onClick={onAutoLayout}
          disabled={layoutDisabled}
          className="flex items-center gap-1.5 px-2.5 h-7 rounded bg-surface-container-low hover:bg-surface-container text-on-surface font-body-sm text-body-sm border border-outline-variant/40 transition-colors"
          title="Organizar en cuadrícula después de reservar las clases"
        >
          <span className="material-symbols-outlined text-[16px] text-secondary">hub</span>
          <span>Organizar</span>
        </button>

        <button
          type="button"
          onClick={onToggleSnap}
          className={`flex items-center gap-1.5 px-2.5 h-7 rounded font-body-sm text-body-sm border transition-colors ${
            snapGrid
              ? 'bg-surface-container-high text-on-surface border-secondary'
              : 'bg-surface-container-low text-on-surface-variant border-outline-variant/40'
          }`}
          title="Ajuste magnético a la cuadrícula (16px)"
        >
          <span className="material-symbols-outlined text-[16px] text-secondary">grid_4x4</span>
          <span>Snap: {snapGrid ? `${snapGrid}px` : 'Off'}</span>
        </button>

        <div className="w-px h-5 bg-outline-variant/50 mx-0.5"></div>

        <button
          type="button"
          onClick={onOpenLegacyRef}
          className="flex items-center gap-1.5 px-2.5 h-7 rounded bg-surface-container-low hover:bg-surface-container text-on-surface font-code-sm text-code-sm border border-outline-variant/40 transition-colors"
          title="Comparar modelo UML con formulario tradicional original"
        >
          <span className="material-symbols-outlined text-[15px] text-primary">history_toggle_off</span>
          <span>Ver Origen Form</span>
        </button>
      </div>

      {/* Floating Zoom Controls (Bottom-Right) */}
      <div className="absolute bottom-4 right-4 z-30 flex items-center gap-1 p-1 bg-surface-container-lowest/95 backdrop-blur shadow-md rounded-xl border border-outline-variant/60 select-none">
        <button
          type="button"
          onClick={onZoomOut}
          className="w-6 h-6 flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors"
          title="Alejar zoom"
        >
          <span className="material-symbols-outlined text-[15px]">remove</span>
        </button>
        <span className="font-code-sm text-code-sm text-on-surface px-1.5 font-semibold min-w-10 text-center">
          {Math.round(zoomLevel)}%
        </span>
        <button
          type="button"
          onClick={onZoomIn}
          className="w-6 h-6 flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors"
          title="Acercar zoom"
        >
          <span className="material-symbols-outlined text-[15px]">add</span>
        </button>
        <div className="w-px h-4 bg-outline-variant/50 mx-0.5"></div>
        <button
          type="button"
          onClick={onZoomFit}
          className="w-6 h-6 flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors"
          title="Ajustar diagrama a pantalla"
        >
          <span className="material-symbols-outlined text-[15px]">fullscreen</span>
        </button>
      </div>
    </>
  )
}
