import { api } from '../api.js'

export function generateIdempotencyKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'req-' + Date.now() + '-' + Math.random().toString(36).substring(2, 10)
}

export function hasIAMention(text) {
  if (!text || typeof text !== 'string') return false
  return /(?:^|\s)@IA(?:\s|$|[.,:;!?])/i.test(text)
}

export function stripIAMention(text) {
  if (!text || typeof text !== 'string') return ''
  return text.replace(/@IA(?:\s|$|[.,:;!?])/gi, ' ').replace(/\s+/g, ' ').trim()
}

export function mergeIncomingMessage(existingMessages, incomingMessage) {
  if (!incomingMessage || !incomingMessage.id) return existingMessages
  const index = existingMessages.findIndex(m => m.id === incomingMessage.id)
  let updated
  if (index >= 0) {
    updated = [...existingMessages]
    updated[index] = { ...updated[index], ...incomingMessage }
  } else {
    updated = [...existingMessages, incomingMessage]
  }
  return updated.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
}

export function mergeHistoryPage(existingMessages, newHistoryPage) {
  if (!Array.isArray(newHistoryPage) || newHistoryPage.length === 0) return existingMessages
  const map = new Map()
  for (const msg of newHistoryPage) {
    if (msg?.id) map.set(msg.id, msg)
  }
  for (const msg of existingMessages) {
    if (msg?.id) map.set(msg.id, msg)
  }
  return Array.from(map.values()).sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
}

export async function fetchProjectMessages(projectId, token, { limit = 50, before = null } = {}) {
  let query = `?limit=${encodeURIComponent(limit)}`
  if (before) query += `&before=${encodeURIComponent(before)}`
  return await api(`/projects/${projectId}/messages${query}`, { token })
}

export async function postChatMessage(projectId, token, content) {
  return await api(`/projects/${projectId}/messages`, {
    token,
    method: 'POST',
    body: { content }
  })
}


export async function postHelpRequest(projectId, token, { userPrompt, sourceMessageId = null, idempotencyKey = null }) {
  const key = idempotencyKey || generateIdempotencyKey()
  return await api(`/projects/${projectId}/help-requests`, {
    token,
    method: 'POST',
    body: {
      content: userPrompt,
      source_message_id: sourceMessageId,
      idempotency_key: key
    }
  })
}


export async function getHelpRequestStatus(projectId, token, helpRequestId) {
  return await api(`/projects/${projectId}/help-requests/${helpRequestId}`, { token })
}

export function formatMessageTime(isoString) {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    if (isNaN(date.getTime())) return ''
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}
