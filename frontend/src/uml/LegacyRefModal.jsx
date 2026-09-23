export function LegacyRefModal({ isOpen, onClose }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-inverse-surface/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 select-none">
      <div className="bg-surface-container-lowest rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden border border-outline-variant/60">
        <div className="h-10 px-4 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-[18px]">schema</span>
            <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
              Reemplazo Arquitectural: Formulario Web Tradicional vs Modelo UML 2.5
            </span>
          </div>
          <button
            type="button"
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container text-on-surface-variant transition-colors"
            onClick={onClose}
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div className="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Columna 1: Formulario Tradicional */}
          <div className="flex flex-col gap-3 bg-surface-container-low p-4 rounded-lg border border-outline-variant/40">
            <span className="font-label-caps text-label-caps text-on-surface-variant tracking-wider font-bold">
              Formulario Previo (Captura Original)
            </span>
            <div className="overflow-hidden rounded-lg max-h-72 flex items-center justify-center bg-surface-container p-3 border border-outline-variant/30">
              <div className="flex flex-col gap-2 w-full text-xs font-mono text-on-surface-variant">
                <div className="p-2 bg-white rounded border">
                  <strong>Formulario de Cliente / Vehículo</strong>
                  <div className="mt-1 text-[11px] text-gray-500">Inputs apilados secuencialmente sin relaciones explícitas</div>
                </div>
                <div className="p-2 bg-white rounded border opacity-75">Campos: Nombre, Apellido, Email, Teléfono, Placa, Marca...</div>
              </div>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              El flujo tradicional apilaba atributos en un formulario rígido. Este modelador UML visualiza entidades desacopladas, cardinalidades y métodos Spring Data JPA.
            </p>
          </div>

          {/* Columna 2: Mapeo Arquitectural DDD */}
          <div className="flex flex-col gap-4 justify-between">
            <div>
              <span className="font-label-caps text-label-caps text-secondary tracking-wider font-bold">
                Transformación a Dominio DDD &amp; JPA
              </span>
              <h4 className="font-headline-md text-headline-md text-on-surface font-bold mt-1">
                com.example.model :: Dominio Relacional
              </h4>
              <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                Las entidades del diagrama gestionan relaciones 1:1, 1:N y N:M con integridad referencial estricta y operaciones transaccionales.
              </p>

              <div className="mt-4 flex flex-col gap-2 font-code-sm text-code-sm">
                <div className="p-2.5 rounded bg-surface-container flex items-center justify-between text-on-surface border border-outline-variant/30">
                  <span className="font-semibold">Cliente [1] → [0..*] Telefono</span>
                  <span className="text-secondary font-semibold text-[11px]">@OneToMany(cascade = ALL)</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container flex items-center justify-between text-on-surface border border-outline-variant/30">
                  <span className="font-semibold">Cliente [1] ◆→ [1..*] Automovil</span>
                  <span className="text-secondary font-semibold text-[11px]">Composición JPA</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container flex items-center justify-between text-on-surface border border-outline-variant/30">
                  <span className="font-semibold">Automovil [1] → [0..*] HojaServicio</span>
                  <span className="text-secondary font-semibold text-[11px]">@OneToMany / LazyFetch</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end pt-4 border-t border-outline-variant/30">
              <button
                type="button"
                className="px-4 py-2 rounded bg-secondary hover:bg-secondary-container text-on-secondary font-body-sm text-body-sm font-semibold shadow-sm transition-all"
                onClick={onClose}
              >
                Volver al Lienzo Interactivo
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
