import { useState } from 'react'
import { multiplicities, relations, types } from './document'

function CompactInput({ label, value, onChange, placeholder, disabled, ...props }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="font-code-sm text-code-sm text-on-surface-variant font-medium">
        {label}
      </label>
      <input
        type="text"
        value={props.defaultValue !== undefined ? undefined : value ?? ''}
        disabled={disabled}
        placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        className="px-2.5 py-1 bg-surface-container-low text-on-surface border border-outline-variant/60 rounded font-code-sm text-code-sm outline-none focus:ring-1 focus:ring-secondary focus:bg-surface-container-lowest transition-all disabled:opacity-50"
        {...props}
      />
    </div>
  )
}

function CompactSelect({ label, value, onChange, options, disabled }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="font-code-sm text-code-sm text-on-surface-variant font-medium">
        {label}
      </label>
      <select
        value={value ?? ''}
        disabled={disabled}
        onChange={e => onChange(e.target.value)}
        className="px-2.5 py-1 bg-surface-container-low text-on-surface border border-outline-variant/60 rounded font-code-sm text-code-sm outline-none focus:ring-1 focus:ring-secondary disabled:opacity-50"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

export function Inspector({
  node,
  edge,
  nodes = [],
  disabled,
  editing,
  editUnavailable,
  onStartEditing,
  updateNode,
  updateEdge,
  onDelete,
  shared,
}) {
  const [activeTab, setActiveTab] = useState('attributes')
  const [showParticipants, setShowParticipants] = useState(false)
  const data = node?.data
  const reservations = shared?.reservations || []
  const participants = shared?.participants || []

  const setData = (key, value) => updateNode({ ...data, [key]: value })
  const setItem = (collection, index, key, value) =>
    setData(collection, data[collection].map((item, i) => (i === index ? { ...item, [key]: value } : item)))

  const classTypes = [...new Set(nodes.map(n => `${n.data.package_name}.${n.data.name}`))]

  return (
    <aside className="w-80 bg-surface-container-lowest border-l border-outline-variant/60 flex flex-col h-full select-none z-30 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
      {/* Header Superior: Inspector de Propiedades */}
      <div className="h-8 px-3 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40 flex-shrink-0">
        <span className="font-label-caps text-label-caps text-on-surface-variant tracking-wider">
          Inspector de Propiedades
        </span>
        <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
          tune
        </span>
      </div>

      <datalist id="uml-multiplicities">
        {multiplicities.map(value => (
          <option key={value} value={value} />
        ))}
      </datalist>

      {/* Contenido del Inspector */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {!node && !edge && (
          <div className="py-8 text-center text-on-surface-variant font-body-sm text-xs bg-surface-container-low/50 rounded-lg p-4 border border-dashed border-outline-variant/50">
            <span className="material-symbols-outlined text-[28px] text-secondary/60 mb-2 block">
              touch_app
            </span>
            Selecciona una clase o relación en el lienzo para inspeccionar y modificar sus atributos, métodos o cardinalidades.
          </div>
        )}

        {(node || edge) && (
          <div className="p-2.5 rounded border border-outline-variant/40 text-xs flex flex-col gap-2">
            <p>{editing ? 'Edición reservada para ti. Usa «Guardar y terminar edición» para liberar las clases.' : 'Modo consulta: seleccionar no reserva clases. Para modificar o mover, inicia la edición.'}</p>
            {!editing && <button type="button" onClick={onStartEditing} disabled={editUnavailable}
              className="px-3 py-2 rounded bg-secondary text-on-secondary disabled:opacity-40 disabled:cursor-not-allowed">
              {node ? 'Editar y mover' : 'Editar relación'}
            </button>}
            {!editing && editUnavailable && <p>La edición no está disponible: comprueba la conexión, tus permisos y las reservas.</p>}
          </div>
        )}

        <fieldset disabled={disabled} className="border-0 p-0 m-0 flex flex-col gap-3">
          {/* Edición de Clase UML */}
          {data && (
            <>
              <div className="bg-surface-container-low/40 p-2.5 rounded-lg border border-outline-variant/40 flex flex-col gap-2.5">
                <CompactSelect label="Tipo UML" value={data.kind || 'class'}
                  options={[{ value: 'class', label: 'Clase' }, { value: 'interface', label: 'Interfaz' }, { value: 'enumeration', label: 'Enumeración' }]}
                  onChange={kind => updateNode({ ...data, kind, literals: kind === 'enumeration' ? data.literals || [] : [] })} />
                <CompactInput label="Parámetros de plantilla (ej. T, U)"
                  key={`${node.id}:template:${JSON.stringify(data.template_parameters)}`}
                  defaultValue={(data.template_parameters || []).join(', ')} onChange={() => {}}
                  onBlur={event => setData('template_parameters', event.target.value.split(',').map(value => value.trim()).filter(Boolean))} />
                {data.kind === 'enumeration' && <CompactInput label="Literales (separados por comas)" key={`${node.id}:${JSON.stringify(data.literals)}`} defaultValue={(data.literals || []).join(', ')}
                  onChange={() => {}} onBlur={event => setData('literals', event.target.value.split(',').map(item => item.trim()).filter(Boolean))} />}
                <CompactInput
                  label="Nombre de Clase"
                  value={data.name}
                  onChange={value => setData('name', value)}
                  maxLength={100}
                  placeholder="Ej. Cliente"
                />

                <CompactInput
                  label="Paquete Destino"
                  value={data.package_name}
                  onChange={value => setData('package_name', value)}
                  maxLength={150}
                  placeholder="com.example.model"
                />

                <label className="flex items-center gap-2 font-code-sm text-code-sm text-on-surface cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={!!data.is_abstract}
                    onChange={e => setData('is_abstract', e.target.checked)}
                    className="w-3.5 h-3.5 text-secondary rounded"
                  />
                  <span>Clase Abstracta «abstract»</span>
                </label>
              </div>

              {/* Pestañas de Atributos / Métodos */}
              <div className="flex border-b border-outline-variant/50 text-xs">
                <button
                  type="button"
                  className={`flex-1 py-1.5 font-semibold text-center transition-colors border-b-2 ${
                    activeTab === 'attributes'
                      ? 'border-secondary text-secondary bg-surface-container-low/50'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                  onClick={() => setActiveTab('attributes')}
                >
                  Atributos ({data.attributes?.length || 0})
                </button>
                <button
                  type="button"
                  className={`flex-1 py-1.5 font-semibold text-center transition-colors border-b-2 ${
                    activeTab === 'methods'
                      ? 'border-secondary text-secondary bg-surface-container-low/50'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                  onClick={() => setActiveTab('methods')}
                >
                  Métodos ({data.methods?.length || 0})
                </button>
              </div>

              {/* Sección Atributos */}
              {activeTab === 'attributes' && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="font-code-sm text-code-sm font-semibold text-on-surface">
                      Atributos (+ / - / #)
                    </span>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        let count = 1
                        while (data.attributes.some(a => a.name === `atributo${count}`)) count++
                        setData('attributes', [
                          ...data.attributes,
                          {
                            name: `atributo${count}`,
                            type: 'String',
                            visibility: '-',
                            is_pk: false,
                            is_nullable: false,
                            is_unique: false,
                            is_static: false,
                            default_value: null,
                          },
                        ])
                      }}
                      className="px-2 py-0.5 bg-secondary text-on-secondary hover:bg-secondary-container rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
                      title="Añadir atributo"
                    >
                      <span className="material-symbols-outlined text-[14px]">add</span>
                      <span>Añadir</span>
                    </button>
                  </div>

                  <div className="flex flex-col gap-1.5 font-code-sm text-code-sm">
                    {data.attributes.map((attribute, index) => (
                      <details
                        key={index}
                        className="bg-surface-container-low p-2 rounded border border-outline-variant/40 group"
                      >
                        <summary className="cursor-pointer flex items-center justify-between font-semibold text-on-surface list-none">
                          <div className="flex items-center gap-1.5 truncate">
                            <span className={
                              attribute.visibility === '+' ? 'text-[#16a34a] font-bold font-mono' :
                              attribute.visibility === '-' ? 'text-[#dc2626] font-bold font-mono' :
                              attribute.visibility === '#' ? 'text-[#d97706] font-bold font-mono' : 'text-secondary font-bold font-mono'
                            }>
                              {attribute.visibility}
                            </span>
                            <span className="truncate">{attribute.name || 'atributo'}</span>
                            <span className="text-on-surface-variant font-normal">: {attribute.type}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            {attribute.is_pk && (
                              <span className="text-[9px] px-1 bg-secondary-fixed text-on-secondary-fixed rounded font-bold">
                                PK
                              </span>
                            )}
                            <span className="material-symbols-outlined text-[14px] text-on-surface-variant group-open:rotate-180 transition-transform">
                              expand_more
                            </span>
                          </div>
                        </summary>

                        <div className="pt-2 mt-2 border-t border-outline-variant/30 flex flex-col gap-2">
                          <CompactInput
                            label="Nombre"
                            value={attribute.name}
                            onChange={val => setItem('attributes', index, 'name', val)}
                          />

                          <div className="grid grid-cols-2 gap-2">
                            <CompactSelect
                              label="Tipo"
                              value={attribute.type}
                              onChange={val => setItem('attributes', index, 'type', val)}
                              options={[
                                ...types.map(t => ({ value: t, label: t })),
                                ...classTypes.map(c => ({ value: c, label: c })),
                              ]}
                            />
                            <CompactSelect
                              label="Visibilidad"
                              value={attribute.visibility}
                              onChange={val => setItem('attributes', index, 'visibility', val)}
                              options={[
                                { value: '+', label: '+ Pública' },
                                { value: '-', label: '- Privada' },
                                { value: '#', label: '# Protegida' },
                                { value: '~', label: '~ Paquete' },
                              ]}
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-1.5 pt-1 text-[11px]">
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!attribute.is_pk}
                                onChange={e => setItem('attributes', index, 'is_pk', e.target.checked)}
                              />
                              <span>Clave PK</span>
                            </label>
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!attribute.is_nullable}
                                onChange={e => setItem('attributes', index, 'is_nullable', e.target.checked)}
                              />
                              <span>Admite Nulo</span>
                            </label>
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!attribute.is_unique}
                                onChange={e => setItem('attributes', index, 'is_unique', e.target.checked)}
                              />
                              <span>Único</span>
                            </label>
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!attribute.is_static}
                                onChange={e => setItem('attributes', index, 'is_static', e.target.checked)}
                              />
                              <span>Estático</span>
                            </label>
                          </div>

                          <button
                            type="button"
                            onClick={() => setData('attributes', data.attributes.filter((_, i) => i !== index))}
                            className="mt-1 py-1 px-2 bg-error-container hover:bg-error hover:text-on-error text-on-error-container rounded text-[11px] font-medium transition-colors flex items-center justify-center gap-1"
                          >
                            <span className="material-symbols-outlined text-[13px]">delete</span>
                            <span>Quitar atributo</span>
                          </button>
                        </div>
                      </details>
                    ))}
                  </div>
                </div>
              )}

              {/* Sección Métodos */}
              {activeTab === 'methods' && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="font-code-sm text-code-sm font-semibold text-on-surface">
                      Métodos / Operaciones
                    </span>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        let count = 1
                        while (data.methods.some(m => m.name === `metodo${count}`)) count++
                        setData('methods', [
                          ...data.methods,
                          {
                            name: `metodo${count}`,
                            return_type: 'void',
                            visibility: '+',
                            parameters: [],
                            is_static: false,
                            is_abstract: false,
                          },
                        ])
                      }}
                      className="px-2 py-0.5 bg-secondary text-on-secondary hover:bg-secondary-container rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
                      title="Añadir método"
                    >
                      <span className="material-symbols-outlined text-[14px]">add</span>
                      <span>Añadir</span>
                    </button>
                  </div>

                  <div className="flex flex-col gap-1.5 font-code-sm text-code-sm">
                    {data.methods.map((method, index) => (
                      <details
                        key={index}
                        className="bg-surface-container-low p-2 rounded border border-outline-variant/40 group"
                      >
                        <summary className="cursor-pointer flex items-center justify-between font-semibold text-on-surface list-none">
                          <div className="flex items-center gap-1.5 truncate">
                            <span className={
                              method.visibility === '+' ? 'text-[#16a34a] font-bold font-mono' :
                              method.visibility === '-' ? 'text-[#dc2626] font-bold font-mono' :
                              method.visibility === '#' ? 'text-[#d97706] font-bold font-mono' : 'text-secondary font-bold font-mono'
                            }>
                              {method.visibility}
                            </span>
                            <span className="truncate">{method.name}()</span>
                            <span className="text-on-surface-variant font-normal">: {method.return_type}</span>
                          </div>
                          <span className="material-symbols-outlined text-[14px] text-on-surface-variant group-open:rotate-180 transition-transform">
                            expand_more
                          </span>
                        </summary>

                        <div className="pt-2 mt-2 border-t border-outline-variant/30 flex flex-col gap-2">
                          <CompactInput
                            label="Nombre del método"
                            value={method.name}
                            onChange={val => setItem('methods', index, 'name', val)}
                          />

                          <div className="grid grid-cols-2 gap-2">
                            <CompactSelect
                              label="Retorno"
                              value={method.return_type}
                              onChange={val => setItem('methods', index, 'return_type', val)}
                              options={[
                                { value: 'void', label: 'void' },
                                ...types.map(t => ({ value: t, label: t })),
                                ...classTypes.map(c => ({ value: c, label: c })),
                              ]}
                            />
                            <CompactSelect
                              label="Visibilidad"
                              value={method.visibility}
                              onChange={val => setItem('methods', index, 'visibility', val)}
                              options={[
                                { value: '+', label: '+ Pública' },
                                { value: '-', label: '- Privada' },
                                { value: '#', label: '# Protegida' },
                                { value: '~', label: '~ Paquete' },
                              ]}
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-1.5 pt-1 text-[11px]">
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!method.is_abstract}
                                onChange={e => setItem('methods', index, 'is_abstract', e.target.checked)}
                              />
                              <span>Abstracto</span>
                            </label>
                            <label className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!method.is_static}
                                onChange={e => setItem('methods', index, 'is_static', e.target.checked)}
                              />
                              <span>Estático</span>
                            </label>
                          </div>

                          {/* Parámetros del método */}
                          <div className="mt-1 pt-2 border-t border-outline-variant/30 flex flex-col gap-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-[11px]">Parámetros</span>
                              <button
                                type="button"
                                onClick={() => {
                                  let count = 1
                                  while (method.parameters.some(p => p.name === `param${count}`)) count++
                                  setItem('methods', index, 'parameters', [
                                    ...method.parameters,
                                    { name: `param${count}`, param_type: 'String' },
                                  ])
                                }}
                                className="text-secondary text-[11px] hover:underline font-semibold"
                              >
                                + Parámetro
                              </button>
                            </div>

                            {method.parameters.map((p, pIndex) => (
                              <div key={pIndex} className="flex items-center gap-1 bg-surface-container p-1 rounded">
                                <input
                                  type="text"
                                  value={p.name}
                                  placeholder="nombre"
                                  onChange={e =>
                                    setItem(
                                      'methods',
                                      index,
                                      'parameters',
                                      method.parameters.map((item, pi) =>
                                        pi === pIndex ? { ...item, name: e.target.value } : item
                                      )
                                    )
                                  }
                                  className="w-1/2 px-1.5 py-0.5 bg-surface-container-lowest border rounded text-[11px]"
                                />
                                <select
                                  value={p.param_type}
                                  onChange={e =>
                                    setItem(
                                      'methods',
                                      index,
                                      'parameters',
                                      method.parameters.map((item, pi) =>
                                        pi === pIndex ? { ...item, param_type: e.target.value } : item
                                      )
                                    )
                                  }
                                  className="w-1/2 px-1 py-0.5 bg-surface-container-lowest border rounded text-[11px]"
                                >
                                  {types.map(t => <option key={t} value={t}>{t}</option>)}
                                  {classTypes.map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setItem(
                                      'methods',
                                      index,
                                      'parameters',
                                      method.parameters.filter((_, pi) => pi !== pIndex)
                                    )
                                  }
                                  className="text-error hover:text-on-error hover:bg-error p-0.5 rounded"
                                >
                                  <span className="material-symbols-outlined text-[13px]">close</span>
                                </button>
                              </div>
                            ))}
                          </div>

                          <button
                            type="button"
                            onClick={() => setData('methods', data.methods.filter((_, i) => i !== index))}
                            className="mt-1 py-1 px-2 bg-error-container hover:bg-error hover:text-on-error text-on-error-container rounded text-[11px] font-medium transition-colors flex items-center justify-center gap-1"
                          >
                            <span className="material-symbols-outlined text-[13px]">delete</span>
                            <span>Quitar método</span>
                          </button>
                        </div>
                      </details>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Edición de Relación UML */}
          {edge && (
            <div className="bg-surface-container-low/40 p-3 rounded-lg border border-outline-variant/40 flex flex-col gap-2.5 font-code-sm text-code-sm">
              <CompactSelect
                label="Tipo de Relación"
                value={edge.type}
                onChange={val => updateEdge({ ...edge, type: val, template_arguments: val === 'template_binding' ? edge.template_arguments || {} : {} })}
                options={Object.entries(relations).map(([k, v]) => ({ value: k, label: v }))}
              />

              <div className="grid grid-cols-2 gap-2">
                <CompactSelect
                  label="Clase Origen"
                  value={edge.source}
                  onChange={val => updateEdge({ ...edge, source: val })}
                  options={nodes.map(n => ({ value: n.id, label: n.data.name }))}
                />
                <CompactSelect
                  label="Clase Destino"
                  value={edge.target}
                  onChange={val => updateEdge({ ...edge, target: val })}
                  options={nodes.map(n => ({ value: n.id, label: n.data.name }))}
                />
              </div>

              {edge.type === 'association_class' && (
                <p>Clase vinculada: <strong>{nodes.find(n => n.id === edge.association_node_id)?.data.name || 'Se creará al editar esta relación'}</strong>.
                  Selecciona su recuadro para editar nombre y atributos. La línea discontinua conserva el vínculo al moverla.</p>
              )}

              {!['generalization', 'dependency'].includes(edge.type) && (
                <div className="grid grid-cols-2 gap-2">
                  <CompactInput
                    label="Multiplicidad Origen"
                    value={edge.source_cardinality}
                    list="uml-multiplicities"
                    onChange={val => updateEdge({ ...edge, source_cardinality: val })}
                  />
                  <CompactInput
                    label="Multiplicidad Destino"
                    value={edge.target_cardinality}
                    list="uml-multiplicities"
                    onChange={val => updateEdge({ ...edge, target_cardinality: val })}
                  />
                </div>
              )}

              {edge.type === 'template_binding' && (
                <div className="flex flex-col gap-2">
                  <p>Define los parámetros en la clase destino y aquí el tipo que sustituye a cada uno. Usa un tipo básico o el nombre completo de una clase.</p>
                  {!(nodes.find(n => n.id === edge.target)?.data.template_parameters || []).length && <p>El destino todavía no tiene parámetros de plantilla.</p>}
                  {[...new Set([...(nodes.find(n => n.id === edge.target)?.data.template_parameters || []), ...Object.keys(edge.template_arguments || {})])].map(parameter => (
                    <CompactInput key={`${edge.id}:${parameter}:${edge.template_arguments?.[parameter] || ''}`}
                      label={`Sustituir ${parameter} por`} defaultValue={edge.template_arguments?.[parameter] || ''} onChange={() => {}}
                      onBlur={event => {
                        const args = { ...edge.template_arguments }
                        const value = event.target.value.trim()
                        if (value) args[parameter] = value
                        else delete args[parameter]
                        updateEdge({ ...edge, template_arguments: args })
                      }} />
                  ))}
                </div>
              )}
              <CompactInput
                label="Nombre / Rol de la Relación"
                value={edge.relation_name || ''}
                onChange={val => updateEdge({ ...edge, relation_name: val || null })}
                maxLength={150}
                placeholder="Ej. tiene, posee"
              />
            </div>
          )}

          {/* Botón Eliminar Elemento */}
          {(node || edge) && (
            <button
              type="button"
              disabled={disabled}
              onClick={onDelete}
              className="mt-2 py-1.5 px-3 bg-error-container hover:bg-error hover:text-on-error text-on-error-container rounded text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 border border-error/30 disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[16px]">delete_forever</span>
              <span>Eliminar {node ? 'Clase' : 'Relación'}</span>
            </button>
          )}
        </fieldset>
      </div>

      {/* Sección Inferior: Colaboración en Vivo */}
      <div className="mt-auto border-t border-outline-variant/60 flex-shrink-0 bg-surface-container-lowest">
        <div className="h-8 px-3 bg-surface-container-low flex items-center justify-between border-b border-outline-variant/40">
          <span className="font-label-caps text-label-caps text-on-surface-variant tracking-wider">
            Colaboración en Vivo
          </span>
          <span className="material-symbols-outlined text-[16px] text-secondary">
            group
          </span>
        </div>

        <div className="p-2.5 bg-surface-container-lowest flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
              <span className="font-body-sm text-body-sm text-on-surface font-medium">
                {participants.length} {participants.length === 1 ? 'Diseñador' : 'Diseñadores'} en línea
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowParticipants(s => !s)}
              className="px-2 py-0.5 bg-surface-container-low hover:bg-surface-container text-on-surface text-[11px] rounded transition-colors font-code-sm"
            >
              {showParticipants ? 'Ocultar' : 'Ver equipo'}
            </button>
          </div>

          {/* Lista desplegable de participantes y bloqueos activos */}
          {showParticipants && (
            <div className="flex flex-col gap-1 pt-1 border-t border-outline-variant/30 max-h-32 overflow-y-auto text-[11px] font-code-sm">
              {participants.map(p => {
                const isMe = p.connection_id === shared?.connectionId
                const userLocks = reservations.filter(r => r.connection_id === p.connection_id)
                return (
                  <div key={p.connection_id} className="p-1.5 rounded bg-surface-container-low flex flex-col gap-0.5">
                    <div className="flex items-center justify-between text-on-surface">
                      <span className="font-semibold truncate">
                        {p.name} {isMe ? '(Tú)' : ''}
                      </span>
                      <span className="text-[10px] text-secondary">{p.role}</span>
                    </div>
                    {userLocks.length > 0 && (
                      <div className="text-[10px] text-on-surface-variant flex items-center gap-1">
                        <span className="material-symbols-outlined text-[12px] text-secondary">lock</span>
                        <span>Editando: {userLocks.map(l => nodes.find(n => n.id === l.node_id)?.data.name || 'Clase').join(', ')}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
