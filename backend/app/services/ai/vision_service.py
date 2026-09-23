"""Validate inline attachments; no paths, external URLs or persistent uploads."""
import base64
import binascii
from fastapi import HTTPException

MAX_BODY = 12 * 1024 * 1024
MAX_TOTAL_MEDIA = 8 * 1024 * 1024


def decode_attachments(attachments):
    result, total = [], 0
    for item in attachments:
        try:
            raw = base64.b64decode(item.data, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, 'Un adjunto contiene base64 inválido.') from None
        limit = (4 if item.mime_type.startswith('image/') else 6) * 1024 * 1024
        if len(raw) > limit:
            raise HTTPException(413, 'Máximo 4 MiB por imagen y 6 MiB por audio.')
        total += len(raw)
        if total > MAX_TOTAL_MEDIA:
            raise HTTPException(413, 'Los adjuntos superan 8 MiB en total.')
        signatures = {
            'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'),
            'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
            'image/webp': raw.startswith(b'RIFF') and raw[8:12] == b'WEBP',
            'audio/wav': raw.startswith(b'RIFF') and raw[8:12] == b'WAVE',
            'audio/ogg': raw.startswith(b'OggS'),
            'audio/webm': raw.startswith(b'\x1a\x45\xdf\xa3'),
            'audio/mpeg': raw.startswith(b'ID3') or (len(raw) >= 2 and raw[0] == 255 and raw[1] & 224 == 224),
        }
        if len(raw) < 12 or not signatures[item.mime_type]:
            raise HTTPException(422, 'El contenido de un adjunto no coincide con su formato declarado.')
        result.append((item.mime_type, raw))
    return result
