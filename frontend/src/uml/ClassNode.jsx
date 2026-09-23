import { Handle, Position, NodeResizer } from '@xyflow/react'

export function ClassNode({ data, selected, isConnectable }) {
  const isAbstract = data.is_abstract
  const stereotype = data.kind === 'interface' ? '«interface»' : data.kind === 'enumeration' ? '«enumeration»' : isAbstract ? '«abstract»' : '«entity»'

  return (
    <div
      className={`relative w-full h-full min-w-[200px] min-h-[110px] bg-surface-container-lowest rounded-lg border transition-shadow select-none group font-sans flex flex-col ${
        selected
          ? 'border-secondary ring-2 ring-secondary shadow-xl z-20'
          : 'border-outline-variant/60 shadow-md hover:shadow-lg z-10'
      }`}
    >
      <NodeResizer
        isVisible={selected && data.canResize}
        minWidth={200}
        minHeight={110}
        maxWidth={10000}
        maxHeight={10000}
        color="#0051d5"
        handleClassName="!w-2.5 !h-2.5 !bg-[#0051d5] !border-2 !border-white !rounded-xs shadow-md"
        lineClassName="!border-[#0051d5]/60"
      />

      {/* Handles de Conexión en los 4 extremos */}
      <Handle
        type="target"
        position={Position.Left}
        id="target-left"
        isConnectable={isConnectable}
        className="!w-2 !h-2 !bg-secondary !border-0 !rounded-xs !-left-1"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="source-right"
        isConnectable={isConnectable}
        className="!w-2 !h-2 !bg-secondary !border-0 !rounded-xs !-right-1"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="target-top"
        isConnectable={isConnectable}
        className="!w-2 !h-2 !bg-secondary !border-0 !rounded-xs !-top-1 opacity-0 group-hover:opacity-100 transition-opacity"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source-bottom"
        isConnectable={isConnectable}
        className="!w-2 !h-2 !bg-secondary !border-0 !rounded-xs !-bottom-1 opacity-0 group-hover:opacity-100 transition-opacity"
      />

      {/* Pill de Reserva / Bloqueo Exclusivo (RF-27) */}
      {data.reservationLabel && (
        <div className="absolute -top-3.5 left-2 z-30 flex items-center gap-1 px-2 py-0.5 bg-secondary text-on-secondary rounded-full shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span>
          <span className="font-code-sm text-[9px] uppercase tracking-wider font-semibold truncate max-w-[190px]">
            Bloqueado • {data.reservationLabel}
          </span>
        </div>
      )}

      {/* Compartimento de Cabecera (Header Compartment) */}
      <div className="p-2 bg-surface-container-high rounded-t-lg text-center border-b border-outline-variant/40 flex-shrink-0">
        <div className="font-code-sm text-[10px] text-on-surface-variant italic font-semibold">
          {stereotype}
        </div>
        <div className={`font-headline-sm text-headline-sm text-on-surface font-bold tracking-tight truncate ${isAbstract ? 'italic' : ''}`}>
          {data.name}
        </div>
        <div className="font-code-sm text-[9px] text-secondary font-mono truncate">
          {data.package_name || 'com.example.model'}
        </div>
      </div>

      {data.kind === 'enumeration' && <div className="p-2 font-mono text-xs border-b">{(data.literals || []).map(value => <div key={value}>{value}</div>)}</div>}
      {/* Compartimento de Atributos */}
      <div className="p-2 bg-surface-container-lowest flex flex-col gap-0.5 font-code-sm text-code-sm text-on-surface flex-1 min-h-[30px] overflow-hidden">
        {data.attributes?.length ? (
          data.attributes.map((attribute, index) => {
            const visColor =
              attribute.visibility === '+' ? 'text-[#16a34a]' :
              attribute.visibility === '-' ? 'text-[#dc2626]' :
              attribute.visibility === '#' ? 'text-[#d97706]' : 'text-secondary'

            return (
              <div
                key={index}
                className={`flex items-center justify-between hover:bg-surface-container-low px-1 py-0.5 rounded ${
                  attribute.is_static ? 'underline' : ''
                }`}
              >
                <div className="flex items-center gap-1 truncate">
                  <strong className={`${visColor} font-mono text-[11px]`}>
                    {attribute.visibility}
                  </strong>
                  <span className="truncate">{attribute.name}</span>
                  <span className="text-on-surface-variant">: {attribute.type}</span>
                  {attribute.default_value !== null && attribute.default_value !== undefined && (
                    <span className="text-on-surface-variant/80 font-normal"> = {attribute.default_value}</span>
                  )}
                </div>
                {attribute.is_pk && (
                  <span className="font-code-sm text-[9px] px-1 bg-secondary-fixed text-on-secondary-fixed rounded font-bold ml-1 flex-shrink-0">
                    PK
                  </span>
                )}
              </div>
            )
          })
        ) : (
          <span className="text-on-surface-variant/50 text-[11px] italic px-1">Sin atributos</span>
        )}
      </div>

      {/* Divisor Hairline */}
      <div className="h-px bg-outline-variant/40 w-full flex-shrink-0"></div>

      {/* Compartimento de Operaciones / Métodos */}
      <div className="p-2 bg-surface-container-lowest rounded-b-lg flex flex-col gap-0.5 font-code-sm text-code-sm text-on-surface flex-1 min-h-[30px] overflow-hidden">
        {data.methods?.length ? (
          data.methods.map((method, index) => {
            const visColor =
              method.visibility === '+' ? 'text-[#16a34a]' :
              method.visibility === '-' ? 'text-[#dc2626]' :
              method.visibility === '#' ? 'text-[#d97706]' : 'text-secondary'

            return (
              <div
                key={index}
                className={`hover:bg-surface-container-low px-1 py-0.5 rounded truncate ${
                  method.is_abstract ? 'italic' : ''
                } ${method.is_static ? 'underline' : ''}`}
                title={`${method.name}(${method.parameters?.map(p => `${p.name}: ${p.param_type}`).join(', ')}): ${method.return_type}`}
              >
                <strong className={`${visColor} font-mono text-[11px] mr-1`}>
                  {method.visibility}
                </strong>
                <span>{method.name}({method.parameters?.length ? method.parameters.map(p => `${p.name}`).join(', ') : ''})</span>
                <span className="text-on-surface-variant">: {method.return_type}</span>
              </div>
            )
          })
        ) : (
          <span className="text-on-surface-variant/50 text-[11px] italic px-1">Sin métodos</span>
        )}
      </div>
    </div>
  )
}
