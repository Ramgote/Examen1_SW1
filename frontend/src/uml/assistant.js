export const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']
export const AUDIO_TYPES = ['audio/webm', 'audio/ogg', 'audio/wav', 'audio/mpeg']
export const MAX_MEDIA = 8 * 1024 * 1024

export function mediaType(file) {
  const mime = file.type.split(';')[0].toLowerCase()
  if (mime === 'audio/x-wav') return 'audio/wav'
  if (mime === 'audio/mp3') return 'audio/mpeg'
  return mime
}

export function validateFiles(files) {
  let images = 0, audio = 0, total = 0
  for (const file of files) {
    const mime = mediaType(file)
    const image = IMAGE_TYPES.includes(mime)
    if (!image && !AUDIO_TYPES.includes(mime)) throw new Error('Formatos admitidos: PNG, JPEG, WebP, WAV, MP3, OGG y WebM de audio.')
    if (!file.size || file.size > (image ? 4 : 6) * 1024 * 1024) throw new Error('Máximo 4 MiB por imagen y 6 MiB por audio; el archivo no puede estar vacío.')
    if (file.name.length > 160) throw new Error('Acorta el nombre del archivo a 160 caracteres.')
    if (image) images++; else audio++
    total += file.size
  }
  if (images > 3 || audio > 1) throw new Error('Puedes combinar hasta tres imágenes y un audio.')
  if (total > MAX_MEDIA) throw new Error('Los adjuntos no pueden superar 8 MiB en total.')
}

export function encodeFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('No se pudo leer el adjunto.'))
    reader.onload = () => resolve({ name: file.name, mime_type: mediaType(file), data: reader.result.split(',')[1] })
    reader.readAsDataURL(file)
  })
}

export function canApplyProposal(proposal, shared) {
  return !!proposal?.changes?.length && proposal.version === shared.diagram?.version &&
    shared.role !== 'VIEWER' && shared.ready && !shared.dirty && !shared.pending && !shared.blocked
}
