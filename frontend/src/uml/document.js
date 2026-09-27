import { newId } from './id.js'

export const types = ['String', 'Integer', 'Long', 'Double', 'Float', 'Boolean', 'BigDecimal', 'LocalDate', 'LocalDateTime', 'Text']
export const relations = {
  association: 'Associate (Asociación)',
  generalization: 'Generalize (Herencia)',
  composition: 'Compose (Composición)',
  aggregation: 'Aggregate (Agregación)',
  association_class: 'Association Class (Clase de Asociación)',
  realization: 'Realize (Realización)',
  template_binding: 'Template Binding (Vinculación)',
  dependency: 'Dependency (Dependencia)'
}
export const multiplicities = ['1', '0..1', '*', '0..*', '1..*']

export function newClass(nodes, kind = 'class') {
  const prefix = kind === 'interface' ? 'Interfaz' : kind === 'enumeration' ? 'Tipo' : 'Clase'
  let number = 1
  while (nodes.some(node => node.data.name === `${prefix}${number}`)) number++
  return { id: newId(), type: 'uml_class', position: { x: 60 + (nodes.length % 4) * 300, y: 60 + Math.floor(nodes.length / 4) * 240 },
    data: { name: `${prefix}${number}`, kind, literals: [], package_name: 'com.example.model', is_abstract: false, attributes: [], methods: [] } }
}

export function newRelation(source, target, type) {
  return { id: newId(), source, target, type, source_cardinality: '1', target_cardinality: '*', source_role: null, target_role: null, relation_name: null }
}

export function newAssociationClass(nodes, sourceNode, targetNode) {
  const sourceName = sourceNode?.data?.name || 'Origen'
  const targetName = targetNode?.data?.name || 'Destino'
  let baseName = `Detalle${sourceName}`
  if (nodes.some(n => n.data.name === baseName)) {
    baseName = `${sourceName}${targetName}`
  }
  let assocName = baseName
  let num = 1
  while (nodes.some(n => n.data.name === assocName)) {
    assocName = `${baseName}${++num}`
  }
  const posX = Math.round(((sourceNode?.position?.x ?? 60) + (targetNode?.position?.x ?? 360)) / 2)
  const posY = Math.round(Math.max(sourceNode?.position?.y ?? 60, targetNode?.position?.y ?? 60) + 160)
  return {
    id: newId(),
    type: 'uml_class',
    position: { x: posX, y: posY },
    data: {
      name: assocName,
      kind: 'class',
      literals: [],
      package_name: sourceNode?.data?.package_name || 'com.example.model',
      is_abstract: false,
      attributes: [],
      methods: []
    }
  }
}

export function removeClass(diagram, id) {
  return { ...diagram, nodes: diagram.nodes.filter(node => node.id !== id), edges: diagram.edges.filter(edge => edge.source !== id && edge.target !== id && edge.association_node_id !== id) }
}

// No persistimos propiedades internas como selected, measured o dragging de React Flow.
export function serializeDiagram(diagram, viewport) {
  return { schema_version: 1, version: diagram.version,
    nodes: diagram.nodes.map(({ id, position, data, width, height }) => ({ id, type: 'uml_class', position, data, ...(width != null ? { width } : {}), ...(height != null ? { height } : {}) })),
    edges: diagram.edges.map(({ id, source, target, type, source_cardinality, target_cardinality, source_role, target_role, relation_name, source_handle, target_handle, template_arguments, association_node_id }) =>
      ({ id, source, target, type, source_cardinality, target_cardinality, source_role, target_role, relation_name, ...(source_handle ? { source_handle } : {}), ...(target_handle ? { target_handle } : {}), ...(template_arguments ? { template_arguments } : {}), ...(association_node_id ? { association_node_id } : {}) })),
    metadata: { viewport: viewport || diagram.metadata.viewport || null } }
}
