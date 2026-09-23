"""Single-process rooms; PostgreSQL is the durable source of truth."""
import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from weakref import WeakValueDictionary

from fastapi import HTTPException, WebSocket
from jose import JWTError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import token_subject
from app.models.user import User
from app.models.canvas import CanvasSnapshot
from app.services.canvas import document
from app.services.projects import project_access
from app.services.websocket.merge import merge_documents, MergeConflict
from app.schemas.uml import UMLCanvasDiagram
from app.services.websocket.reservations import Reservations, affected_classes

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Peer:
    socket: WebSocket
    project_id: UUID
    token: str = field(repr=False)
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ''
    name: str = ''
    role: str = ''
    version: int = 0
    sending: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send(self, message):
        try:
            async with asyncio.timeout(3):
                async with self.sending:
                    await self.socket.send_json(message)
            return True
        except (TimeoutError, RuntimeError, OSError):
            await self.close(1013)
            return False

    async def close(self, code):
        try:
            async with asyncio.timeout(1):
                await self.socket.close(code=code)
        except (TimeoutError, RuntimeError, OSError):
            pass


async def authorize(db, peer, *, write=False):
    try:
        user_id = token_subject(peer.token)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(401, 'Tu sesión expiró. Vuelve a iniciar sesión.')
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, 'Usuario inactivo o sesión inválida')
    _, role = await project_access(db, peer.project_id, user,
                                   {'OWNER', 'EDITOR'} if write else None, lock=write)
    peer.user_id, peer.name, peer.role = str(user.id), user.full_name or 'Participante', role


class ConnectionManager:
    def __init__(self):
        self.rooms = {}
        self.locks = WeakValueDictionary()
        self.reservations = Reservations()

    def lock(self, project_id):
        lock = self.locks.get(project_id)
        if lock is None:
            lock = asyncio.Lock()
            self.locks[project_id] = lock
        return lock

    async def join(self, peer):
        async with self.lock(peer.project_id):
            async with AsyncSessionLocal() as db:
                await authorize(db, peer)
            self.rooms.setdefault(peer.project_id, set()).add(peer)
            await self._refresh(peer.project_id)

    async def leave(self, peer):
        async with self.lock(peer.project_id):
            room = self.rooms.get(peer.project_id, set())
            room.discard(peer)
            # A broken connection keeps its leases only until their 45s expiry.
            if not room:
                self.rooms.pop(peer.project_id, None)
            else:
                await self._refresh(peer.project_id)

    async def _refresh(self, project_id, origin=None, op_id=None):
        room = self.rooms.get(project_id, set())
        if not room:
            return
        # Fresh authorization before every broadcast, including permission changes.
        async with AsyncSessionLocal() as db:
            for peer in list(room):
                try:
                    await authorize(db, peer)
                except HTTPException as exc:
                    room.discard(peer)
                    self.reservations.release(project_id, peer.id)
                    await peer.close(4401 if exc.status_code == 401 else 4403)
                else:
                    if peer.role == 'VIEWER':
                        self.reservations.release(project_id, peer.id)
            snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
            payload = document(snapshot).model_dump(mode='json') if snapshot else None
        if not room:
            self.rooms.pop(project_id, None)
            return
        participants = [dict(connection_id=p.id, user_id=p.user_id, name=p.name, role=p.role)
                        for p in sorted(room, key=lambda p: p.id)]

        async def deliver(peer):
            if payload and (payload['version'] != peer.version or peer is origin):
                ok = await peer.send({'type': 'snapshot', 'document': payload,
                    'op_id': op_id if peer is origin else None, 'role': peer.role})
                if not ok:
                    room.discard(peer)
                    return
                peer.version = payload['version']
            if not await peer.send({'type': 'presence', 'participants': participants,
                                    'connection_id': peer.id, 'role': peer.role,
                                    'reservations': self.reservations.public(project_id)}):
                room.discard(peer)
        await asyncio.gather(*(deliver(peer) for peer in list(room)))

    async def update(self, peer, event):
        async with self.lock(peer.project_id):
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await authorize(db, peer, write=True)
                    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == peer.project_id))
                    if snapshot is None:
                        raise HTTPException(404, 'Lienzo no encontrado')
                    current = document(snapshot).model_dump(mode='json')
                    if event.base.version > current['version']:
                        raise MergeConflict('La versión base es posterior al servidor')
                    merged = merge_documents(event.base.model_dump(mode='json'),
                                             event.document.model_dump(mode='json'), current)
                    # A valid pair of changes can create an invalid combined UML model.
                    merged = UMLCanvasDiagram.model_validate(merged).model_dump(mode='json')
                    # Also reserve changes from clients that did not pre-reserve.
                    # The mutex covers acquisition, commit and publication.
                    self.reservations.acquire(peer.project_id, affected_classes(current, merged), peer)
                    if merged != current:
                        if current['version'] >= 2147483646:
                            raise MergeConflict('Se alcanzó el límite de versiones del proyecto')
                        snapshot.nodes = merged['nodes']
                        snapshot.edges = merged['edges']
                        snapshot.metadata_info = {**merged['metadata'], 'schema_version': 1}
                        snapshot.version += 1
            # Never announce an uncommitted change.
            await self._refresh(peer.project_id, origin=peer, op_id=str(event.op_id))

    async def reserve(self, peer, event):
        async with self.lock(peer.project_id):
            async with AsyncSessionLocal() as db:
                await authorize(db, peer, write=True)
            if event.type == 'release':
                self.reservations.release(peer.project_id, peer.id)
            else:
                self.reservations.acquire(peer.project_id, event.node_ids, peer)
            await self._refresh(peer.project_id)
            await peer.send({'type': 'reservation_ack', 'op_id': str(event.op_id)})

    async def heartbeat(self, peer):
        async with self.lock(peer.project_id):
            async with AsyncSessionLocal() as db:
                await authorize(db, peer)
            if peer.role != 'VIEWER':
                self.reservations.renew(peer.project_id, peer.id)
            else:
                self.reservations.release(peer.project_id, peer.id)
            await peer.send({'type': 'pong'})

    async def poll(self):
        while True:
            await asyncio.sleep(2)
            for project_id, _ in list(self.reservations.items):
                self.reservations.prune(project_id)
            for project_id in list(self.rooms):
                try:
                    async with self.lock(project_id):
                        await self._refresh(project_id)
                except Exception:
                    logger.exception('Error refrescando sala de colaboración')

    async def shutdown(self):
        await asyncio.gather(*(p.close(1001) for room in list(self.rooms.values()) for p in list(room)))
        self.rooms.clear()
        self.reservations.items.clear()


manager = ConnectionManager()
