export const welcome = '¡Hola! Soy tu asistente de modelado UML. ¿En qué quieres que te ayude? Podemos crear clases, revisar relaciones o interpretar un diagrama a partir de una imagen o un audio. Cuéntame qué necesitas.'

export function recentHistory(messages) {
  return messages.slice(-6).map(({ role, content }) => ({ role, content: content.slice(0, 3000) }))
}

export function proposalReply(result) {
  return result.changes.length
    ? `${result.message}\nHe preparado ${result.changes.length} cambios para que los revises. Todavía no están aplicados al diagrama.`
    : `${result.message}\nNo he propuesto cambios en el diagrama.`
}
