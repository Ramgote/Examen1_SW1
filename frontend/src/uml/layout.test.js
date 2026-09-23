import test from 'node:test'
import assert from 'node:assert/strict'
import { arrangeReserved } from './layout.js'
import { newClass, newRelation, serializeDiagram } from './document.js'
import { sameContent, mergeDocuments } from './collaboration.js'

test('layout denied by a reservation never changes the canvas', async () => {
  const nodes = [newClass([])]
  assert.equal(await arrangeReserved({ diagram: { nodes }, reserve: async ids => {
    assert.deepEqual(ids, nodes.map(n => n.id)); return false
  }, change: () => assert.fail('Changed before reservation') }), false)
})

test('layout awaits reservation and does not move newly arrived nodes', async () => {
  const a = newClass([]), b = newClass([a]); a.width = 650
  let resolve
  let changed = false
  const later = newClass([a, b])
  const result = arrangeReserved({ diagram: { nodes: [a, b] }, reserve: () => new Promise(r => { resolve = r }), change: transform => {
    changed = true
    const output = transform({ nodes: [a, b, later] })
    assert.equal(output.nodes[1].position.x, 770)
    assert.deepEqual(output.nodes[2], later)
  } })
  assert.equal(changed, false)
  resolve(true)
  assert.equal(await result, true)
  assert.equal(changed, true)
})

test('visual fields and UML kinds survive serialization without internal measurements', () => {
  const a = newClass([], 'interface'), b = newClass([a], 'interface')
  assert.notEqual(a.data.name, b.data.name)
  const enumeration = newClass([], 'enumeration'); enumeration.data.literals = ['ACTIVO', 'INACTIVO']
  const edge = { ...newRelation(a.id, b.id, 'association'), source_handle: 'source-bottom', target_handle: 'target-top' }
  const output = serializeDiagram({ version: 1, nodes: [{ ...a, width: 450, height: 260, measured: { width: 450 } }, enumeration], edges: [edge], metadata: {} }, { x: 20, y: 40, zoom: 1.5 })
  assert.equal(output.nodes[0].width, 450)
  assert.equal(output.nodes[0].height, 260)
  assert.equal(output.nodes[0].data.kind, 'interface')
  assert.equal(output.nodes[0].measured, undefined)
  assert.deepEqual(output.nodes[1].data.literals, ['ACTIVO', 'INACTIVO'])
  assert.deepEqual(output.edges[0], edge)
  const remote = structuredClone(output); remote.metadata.viewport.x = 70
  assert.equal(sameContent(output, remote), false)
  assert.deepEqual(mergeDocuments(output, output, remote).metadata, remote.metadata)
})
