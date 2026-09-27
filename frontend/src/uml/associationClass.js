export function associationNode(nodes, edge) {
  if (edge.association_node_id) return nodes.find(n => n.id === edge.association_node_id)
  // Compatibility with diagrams saved before explicit references were introduced.
  const matches = nodes.filter(n => n.id !== edge.source && n.id !== edge.target && n.data?.name === edge.relation_name)
  return matches.length === 1 ? matches[0] : null
}

export function associationLink(node, x, y) {
  const width = node.measured?.width ?? node.width ?? 220
  const height = node.measured?.height ?? node.height ?? 100
  const cx = (node.positionAbsolute?.x ?? node.position.x) + width / 2
  const cy = (node.positionAbsolute?.y ?? node.position.y) + height / 2
  const dx = x - cx, dy = y - cy
  const scale = Math.max(Math.abs(dx) / (width / 2), Math.abs(dy) / (height / 2))
  if (scale <= 1) return null
  return `M ${x} ${y} L ${cx + dx / scale} ${cy + dy / scale}`
}
