"""Opt-in integration against the running local Docker API. Removes only its own users."""
import asyncio
import copy
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4, UUID

import httpx
from dotenv import dotenv_values
from jose import jwt
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from app.core.config import Settings
from app.models.user import User


@unittest.skipUnless(os.getenv('RUN_LIVE_WS_TESTS') == '1', 'Requiere API local activa y RUN_LIVE_WS_TESTS=1')
class LiveCollaborationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.http = httpx.AsyncClient(base_url='http://127.0.0.1:8000/api/v1', timeout=15)
        self.users = []; self.sockets = []
        self.config = Settings(**dotenv_values(Path(__file__).resolve().parents[1] / '.env'))

    async def asyncTearDown(self):
        await asyncio.gather(*(socket.close() for socket in self.sockets), return_exceptions=True)
        await self.http.aclose()
        if self.users:
            engine = create_async_engine(self.config.SQLALCHEMY_DATABASE_URI)
            try:
                async with engine.begin() as db:
                    await db.execute(delete(User).where(User.id.in_([UUID(user['id']) for user in self.users])))
            finally:
                await engine.dispose()

    async def request(self, method, path, token=None, data=None, status=200):
        response = await self.http.request(method, path,
            headers={'Authorization': f'Bearer {token}'} if token else {},
            **({'json': data} if data is not None else {}))
        self.assertEqual(response.status_code, status, f'{method} {path}: {response.status_code}')
        return response.json() if status != 204 else None

    async def account(self, name):
        data = {'email': f'ws-{uuid4().hex}@example.test', 'password': 'Sprint3-Only-Test-42', 'full_name': name}
        user = await self.request('POST', '/auth/register', data=data, status=201)
        self.users.append(user)
        result = await self.request('POST', '/auth/login', data={k: data[k] for k in ('email', 'password')})
        return user, result['access_token']

    async def socket(self, project, token):
        socket = await connect(f'ws://127.0.0.1:8000/api/v1/projects/{project}/ws',
                               origin='http://localhost:5173', max_size=4*1024*1024)
        self.sockets.append(socket)
        await socket.send(json.dumps({'type': 'authenticate', 'token': token}))
        return socket

    async def until(self, socket, predicate):
        async with asyncio.timeout(8):
            while True:
                message = json.loads(await socket.recv())
                if predicate(message):
                    return message

    async def snapshot(self, socket, version=None, op_id=None):
        return (await self.until(socket, lambda m: m['type'] == 'snapshot'
            and (version is None or m['document']['version'] >= version)
            and (op_id is None or m['op_id'] == op_id)))['document']

    async def send(self, socket, base, draft, op_id=None):
        op_id = op_id or str(uuid4())
        await socket.send(json.dumps({'type': 'update', 'op_id': op_id, 'base': base, 'document': draft}))
        return op_id

    async def closed(self, socket, code):
        with self.assertRaises(ConnectionClosed) as caught:
            await self.until(socket, lambda _: False)
        self.assertEqual(caught.exception.rcvd.code, code)

    async def test_real_rooms_conflicts_permissions_and_reconnection(self):
        owner, owner_token = await self.account('Owner WS')
        editor, editor_token = await self.account('Editor WS')
        viewer, viewer_token = await self.account('Viewer WS')
        _, outsider_token = await self.account('Outsider WS')
        project = await self.request('POST', '/projects', owner_token, {'name': 'Temporary sprint 3 verification'}, 201)
        pid = project['id']; path = f'/projects/{pid}'
        for user, role in [(editor, 'EDITOR'), (viewer, 'VIEWER')]:
            await self.request('PUT', path + '/members', owner_token, {'email': user['email'], 'role': role})

        with self.subTest('authentication and origin isolation'):
            bad = await self.socket(pid, 'invalid'); await self.closed(bad, 4401)
            outsider = await self.socket(pid, outsider_token); await self.closed(outsider, 4403)
            with self.assertRaises(InvalidStatus):
                async with connect(f'ws://127.0.0.1:8000/api/v1/projects/{pid}/ws', origin='https://untrusted.example'):
                    self.fail('Untrusted origin accepted')
            binary = await self.socket(pid, owner_token); await self.snapshot(binary)
            await binary.send(b'not-json'); await self.closed(binary, 1003)
            oversized = await self.socket(pid, owner_token); await self.snapshot(oversized)
            await oversized.send('x' * (4 * 1024 * 1024 + 1)); await self.closed(oversized, 1009)
        a = await self.socket(pid, owner_token); initial = await self.snapshot(a)
        b = await self.socket(pid, editor_token); await self.snapshot(b)
        c = await self.socket(pid, viewer_token); await self.snapshot(c)
        presence = await self.until(a, lambda m: m['type'] == 'presence' and len(m['participants']) == 3)
        self.assertEqual({p['role'] for p in presence['participants']}, {'OWNER', 'EDITOR', 'VIEWER'})

        with self.subTest('persist and broadcast to all roles'):
            draft = copy.deepcopy(initial)
            draft['nodes'] = [{'id': 'client', 'type': 'uml_class', 'position': {'x': 0, 'y': 0},
                               'data': {'name': 'Cliente'}}]
            op = await self.send(a, initial, draft)
            saved = await self.snapshot(a, op_id=op)
            self.assertEqual(saved, await self.snapshot(b, saved['version']))
            self.assertEqual(saved, await self.snapshot(c, saved['version']))
            self.assertEqual(saved, await self.request('GET', path + '/canvas', owner_token))

        with self.subTest('read-only channel and malformed frames'):
            op = await self.send(c, saved, saved)
            error = await self.until(c, lambda m: m['type'] == 'error' and m['op_id'] == op)
            self.assertEqual(error['code'], 'forbidden')
            await b.send('{broken')
            self.assertEqual((await self.until(b, lambda m: m['type'] == 'error'))['code'], 'validation')
            await b.send(json.dumps({'type': 'ping'}))
            await self.until(b, lambda m: m['type'] == 'pong')
            invalid = copy.deepcopy(saved); invalid['nodes'][0]['data']['name'] = 'invalid name'
            op = await self.send(b, saved, invalid)
            self.assertEqual((await self.until(b, lambda m: m['type'] == 'error' and m['op_id'] == op))['code'], 'validation')
            self.assertEqual(saved, await self.request('GET', path + '/canvas', owner_token))

        with self.subTest('concurrent independent changes merge'):
            left = copy.deepcopy(saved); right = copy.deepcopy(saved)
            left['nodes'][0]['data']['name'] = 'Persona'
            right['nodes'][0]['position']['x'] = 250
            op_a, op_b = await asyncio.gather(self.send(a, saved, left), self.send(b, saved, right))
            await self.snapshot(a, op_id=op_a); await self.snapshot(b, op_id=op_b)
            merged = await self.request('GET', path + '/canvas', owner_token)
            self.assertEqual(merged['version'], saved['version'] + 2)
            self.assertEqual(merged['nodes'][0]['data']['name'], 'Persona')
            self.assertEqual(merged['nodes'][0]['position']['x'], 250)
            await self.snapshot(c, merged['version'])

        with self.subTest('idempotent retry and conflicting edit'):
            op = await self.send(b, saved, right, op_b)
            self.assertEqual((await self.snapshot(b, op_id=op))['version'], merged['version'])
            conflict = copy.deepcopy(saved); conflict['nodes'][0]['data']['name'] = 'Empresa'
            op = await self.send(a, saved, conflict)
            self.assertEqual((await self.until(a, lambda m: m['type'] == 'error' and m['op_id'] == op))['code'], 'conflict')
            self.assertEqual(merged, await self.request('GET', path + '/canvas', owner_token))

        with self.subTest('legacy REST saves reach connected clients'):
            rest = copy.deepcopy(merged); rest['nodes'][0]['data']['is_abstract'] = True
            rest = await self.request('PUT', path + '/canvas', owner_token, rest)
            self.assertEqual(rest, await self.snapshot(c, rest['version']))

        with self.subTest('reconnection reloads durable state and presence leaves'):
            await b.close()
            await self.until(a, lambda m: m['type'] == 'presence' and len(m['participants']) == 2)
            b = await self.socket(pid, editor_token)
            self.assertEqual(rest, await self.snapshot(b))

        with self.subTest('permissions change while socket stays connected'):
            await self.request('PUT', path + '/members', owner_token, {'email': editor['email'], 'role': 'VIEWER'})
            await self.until(b, lambda m: m['type'] == 'presence' and m['role'] == 'VIEWER')
            op = await self.send(b, rest, rest)
            self.assertEqual((await self.until(b, lambda m: m['type'] == 'error' and m['op_id'] == op))['code'], 'forbidden')
            await self.request('DELETE', path + '/members/' + editor['id'], owner_token, status=204)
            await self.closed(b, 4403)

        with self.subTest('JWT expiration closes existing connection'):
            token = jwt.encode({'sub': owner['id'], 'type': 'access',
                'exp': datetime.now(timezone.utc) + timedelta(seconds=3)}, self.config.SECRET_KEY, algorithm='HS256')
            expiring = await self.socket(pid, token); await self.snapshot(expiring)
            await self.closed(expiring, 4401)

        with self.subTest('separate project room does not receive updates'):
            other = await self.request('POST', '/projects', owner_token, {'name': 'Other temporary room'}, 201)
            isolated = await self.socket(other['id'], owner_token)
            isolated_base = await self.snapshot(isolated)
            changed = copy.deepcopy(rest); changed['nodes'][0]['position']['x'] = 450
            op = await self.send(a, rest, changed); await self.snapshot(a, op_id=op)
            self.assertEqual(isolated_base, await self.request('GET', f"/projects/{other['id']}/canvas", owner_token))
            await isolated.send(json.dumps({'type': 'ping'}))
            async with asyncio.timeout(5):
                while True:
                    message = json.loads(await isolated.recv())
                    self.assertNotEqual(message['type'], 'snapshot')
                    if message['type'] == 'pong': break

        with self.subTest('project deletion closes the room'):
            await self.request('DELETE', path, owner_token, status=204)
            await self.closed(a, 4403); await self.closed(c, 4403)


if __name__ == '__main__':
    unittest.main(verbosity=2)
