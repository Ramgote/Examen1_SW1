import test from 'node:test'
import assert from 'node:assert/strict'
import { newClass, newRelation, removeClass, serializeDiagram } from './document.js'

test('eliminar una clase elimina únicamente sus relaciones incidentes', () => {
  const diagram = { nodes: [{ id: 'a' }, { id: 'b' }, { id: 'c' }], edges: [
    { id: 'ab', source: 'a', target: 'b' }, { id: 'bc', source: 'b', target: 'c' }, { id: 'ca', source: 'c', target: 'a' },
  ] }
  const result = removeClass(diagram, 'a')
  assert.deepEqual(result.nodes.map(n => n.id), ['b', 'c'])
  assert.deepEqual(result.edges.map(e => e.id), ['bc'])
  assert.equal(diagram.nodes.length, 3)
})

test('serialización conserva el documento sin campos internos de React Flow', () => {
  const node = newClass([])
  const edge = newRelation(node.id, node.id, 'association')
  const diagram = { version: 4, nodes: [{ ...node, measured: { width: 20 }, selected: true, dragging: true }], edges: [{ ...edge, selected: true }], metadata: {} }
  const viewport = { x: 10, y: 20, zoom: 1.2 }
  const output = serializeDiagram(diagram, viewport)
  assert.deepEqual(output.nodes, [node])
  assert.deepEqual(output.edges, [edge])
  assert.equal(output.version, 4)
  assert.deepEqual(output.metadata.viewport, viewport)
})

test('nuevas clases reciben ids y nombres distintos', () => {
  const first = newClass([])
  const second = newClass([first])
  assert.notEqual(first.id, second.id)
  assert.notEqual(first.data.name, second.data.name)
})

test('template parameters and substitutions survive canvas serialization', () => {
  const source = newClass([]), target = newClass([source])
  target.data.template_parameters = ['T']
  const edge = { ...newRelation(source.id, target.id, 'template_binding'), template_arguments: { T: 'String' } }
  const output = serializeDiagram({ version: 1, nodes: [source, target], edges: [edge], metadata: {} })
  assert.deepEqual(output.nodes[1].data.template_parameters, ['T'])
  assert.deepEqual(output.edges[0].template_arguments, { T: 'String' })
})
