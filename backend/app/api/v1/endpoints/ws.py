import asyncio
import json
import logging
from time import monotonic
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import ValidationError
from app.core.config import settings
from app.services.websocket.connection_manager import manager, Peer
from app.services.websocket.events import Authenticate, Update, ReservationEvent
from app.services.websocket.merge import MergeConflict

router = APIRouter(tags=['Colaboración'])
logger = logging.getLogger(__name__)


async def receive_text(socket):
    message = await socket.receive()
    if message['type'] == 'websocket.disconnect':
        raise WebSocketDisconnect(message.get('code', 1000))
    if message.get('text') is None:
        await socket.close(code=1003)
        raise WebSocketDisconnect(1003)
    return message['text']


@router.websocket('/projects/{project_id}/ws')
async def collaborate(socket: WebSocket, project_id: UUID):
    origin = socket.headers.get('origin')
    if origin and origin not in settings.BACKEND_CORS_ORIGINS:
        await socket.close(code=4403)
        return
    await socket.accept()
    peer = None
    try:
        async with asyncio.timeout(5):
            raw = await receive_text(socket)
            if len(raw.encode('utf-8')) > 10000:
                await socket.close(code=1009)
                return
            auth = Authenticate.model_validate_json(raw)
        peer = Peer(socket=socket, project_id=project_id, token=auth.token)
        await manager.join(peer)
        window, count = monotonic(), 0
        while True:
            raw = await receive_text(socket)
            if len(raw.encode('utf-8')) > 4 * 1024 * 1024:
                await peer.close(1009)
                return
            now = monotonic()
            if now - window >= 1:
                window, count = now, 0
            count += 1
            if count > 20:
                await peer.close(1008)
                return
            op_id = None
            try:
                data = json.loads(raw)
                if data == {'type': 'ping'}:
                    await manager.heartbeat(peer)
                    continue
                if isinstance(data, dict):
                    op_id = str(UUID(str(data.get('op_id'))))
                if isinstance(data, dict) and data.get('type') in {'reserve', 'release'}:
                    await manager.reserve(peer, ReservationEvent.model_validate(data))
                else:
                    event = Update.model_validate(data)
                    await manager.update(peer, event)
            except (ValidationError, ValueError, MergeConflict) as exc:
                conflict = isinstance(exc, MergeConflict)
                # Validation messages only: never echo input values, especially tokens.
                message = '; '.join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()) if isinstance(exc, ValidationError) else str(exc)
                await peer.send({'type': 'error', 'code': 'conflict' if conflict else 'validation',
                                 'message': message[:2000], 'op_id': op_id})
            except HTTPException as exc:
                if exc.status_code == 423:
                    await peer.send({'type': 'error', 'code': 'reserved', 'message': str(exc.detail), 'op_id': op_id})
                    continue
                await peer.send({'type': 'error', 'code': 'forbidden', 'message': str(exc.detail), 'op_id': op_id})
                if exc.status_code != 403:
                    await peer.close(4401 if exc.status_code == 401 else 4403)
                    return
            except Exception:
                logger.exception('Error procesando actualización del lienzo')
                await peer.close(1011)
                return
    except (TimeoutError, ValidationError, HTTPException) as exc:
        await socket.close(code=4403 if isinstance(exc, HTTPException) and exc.status_code != 401 else 4401)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if peer:
            await manager.leave(peer)
