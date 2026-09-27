import test from 'node:test'
import assert from 'node:assert/strict'
import { associationNode, associationLink } from './associationClass.js'
import { newAssociationClass, newRelation, removeClass, serializeDiagram } from './document.js'

test('association class reference survives rename, serialization and delete', () => {
  const a = { id: 'a', position: { x: 0, y: 0 }, data: { name: 'Pedido' } }
  const b = { id: 'b', position: { x: 400, y: 0 }, data: { name: 'Producto' } }
  const linked = newAssociationClass([a, b], a, b)
  const edge = { ...newRelation('a', 'b', 'association_class'), association_node_id: linked.id, relation_name: linked.data.name }
  linked.data.name = 'DetalleRenombrado'
  const diagram = { version: 1, nodes: [a, b, linked], edges: [edge], metadata: {} }
  assert.equal(associationNode(diagram.nodes, edge), linked)
  assert.equal(serializeDiagram(diagram).edges[0].association_node_id, linked.id)
  assert.equal(removeClass(diagram, linked.id).edges.length, 0)
  assert.equal(removeClass(diagram, 'a').nodes.length, 2)
})

test('dashed link follows moved/resized node and meets its border', () => {
  const node = { position: { x: 100, y: 100 }, width: 200, height: 100 }
  assert.equal(associationLink(node, 200, 0), 'M 200 0 L 200 100')
  assert.equal(associationLink(node, 0, 150), 'M 0 150 L 100 150')
  node.position.y = 200
  assert.equal(associationLink(node, 200, 0), 'M 200 0 L 200 200')
  assert.equal(associationLink(node, 200, 250), null)
})
