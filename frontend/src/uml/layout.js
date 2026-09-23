export async function arrangeReserved(shared) {
  const nodes = shared.diagram?.nodes || []
  if (!nodes.length || !await shared.reserve(nodes.map(n => n.id))) return false
  const order = new Map(nodes.map((n, index) => [n.id, index]))
  const cols = Math.max(2, Math.ceil(Math.sqrt(nodes.length)))
  const spacingX = Math.max(300, ...nodes.map(n => (n.width || 200) + 60))
  const spacingY = Math.max(260, ...nodes.map(n => (n.height || 110) + 60))
  shared.change(previous => ({ ...previous, nodes: previous.nodes.map(n => {
    // Nodes added by another participant during the reservation are not ours.
    if (!order.has(n.id)) return n
    const index = order.get(n.id)
    return { ...n, position: { x: 60 + (index % cols) * spacingX, y: 80 + Math.floor(index / cols) * spacingY } }
  }) }))
  return true
}
