"""Explicit live check: run from backend with python tests/smoke_sprint7.py.

Uses disposable users/project, removes only their exact IDs in finally. Requires
the local API on :8000 and .env pointing to the same PostgreSQL database.
"""
import asyncio
import copy
import json
import sys
from pathlib import Path
from uuid import uuid4, UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from websockets.asyncio.client import connect
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal, engine
from app.models.user import User
from app.models.project import Project


async def receive(ws, predicate):
    async with asyncio.timeout(12):
        while True:
            message = json.loads(await ws.recv())
            if predicate(message):
                return message


async def operation(ws, kind, **values):
    op_id = str(uuid4())
    await ws.send(json.dumps(dict(type=kind, op_id=op_id, **values)))
    return await receive(ws, lambda m: m.get('op_id') == op_id)


async def main():
    accounts = []; project_id = None
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000/api/v1', timeout=15) as api:
        try:
            for role in ('owner', 'editor'):
                payload = dict(email=f'sprint7-{uuid4().hex}@example.test', password=uuid4().hex + 'Aa1!', full_name='Prueba ' + role)
                response = await api.post('/auth/register', json=payload); response.raise_for_status()
                account = response.json(); accounts.append(account)
                response = await api.post('/auth/login', json={k: payload[k] for k in ('email', 'password')}); response.raise_for_status()
                account['headers'] = {'Authorization': 'Bearer ' + response.json()['access_token']}
                account['token'] = response.json()['access_token']
            owner, editor = accounts
            response = await api.post('/projects', json={'name': 'Prueba temporal sprint 7'}, headers=owner['headers']); response.raise_for_status()
            project_id = response.json()['id']; path = '/projects/' + project_id
            response = await api.put(path + '/members', json={'email': editor['email'], 'role': 'EDITOR'}, headers=owner['headers']); response.raise_for_status()
            response = await api.put(path + '/canvas', headers=owner['headers'], json=dict(version=1, nodes=[
                dict(id='a', position=dict(x=0, y=0), data=dict(name='Cliente')),
                dict(id='b', position=dict(x=350, y=0), data=dict(name='Venta'))], edges=[])); response.raise_for_status()
            initial = response.json()
            url = 'ws://127.0.0.1:8000/api/v1' + path + '/ws'
            async with connect(url) as a, connect(url) as b:
                for ws, account in ((a, owner), (b, editor)):
                    await ws.send(json.dumps(dict(type='authenticate', token=account['token'])))
                    await receive(ws, lambda m: m['type'] == 'presence')
                assert (await operation(a, 'reserve', node_ids=['a']))['type'] == 'reservation_ack'
                assert (await operation(b, 'reserve', node_ids=['a']))['code'] == 'reserved'
                draft = copy.deepcopy(initial); draft['nodes'][0]['data']['name'] = 'Prohibido'
                assert (await operation(b, 'update', base=initial, document=draft))['code'] == 'reserved'
                draft = copy.deepcopy(initial); draft['nodes'][1]['data']['name'] = 'Pedido'
                assert (await operation(b, 'update', base=initial, document=draft))['type'] == 'snapshot'
                draft = copy.deepcopy(initial); draft['nodes'][0]['data']['name'] = 'Persona'
                result = await operation(a, 'update', base=initial, document=draft)
                assert result['type'] == 'snapshot'
                assert [n['data']['name'] for n in result['document']['nodes']] == ['Persona', 'Pedido']
                draft = copy.deepcopy(result['document']); draft['edges'] = [dict(id='r', source='a', target='b', type='association')]
                response = await api.put(path + '/canvas', headers=editor['headers'], json=draft)
                assert response.status_code == 423
                assert (await operation(a, 'release', node_ids=[]))['type'] == 'reservation_ack'
                assert (await operation(b, 'reserve', node_ids=['a']))['type'] == 'reservation_ack'
                response = await api.put(path + '/members', headers=owner['headers'], json={'email': editor['email'], 'role': 'VIEWER'}); response.raise_for_status()
                await receive(b, lambda m: m['type'] == 'presence' and m['role'] == 'VIEWER')
                assert (await operation(b, 'reserve', node_ids=['a']))['code'] == 'forbidden'
                assert (await operation(a, 'reserve', node_ids=['a', 'b']))['type'] == 'reservation_ack'
            print('OK: sockets reales, contención, edición independiente, HTTP protegido, liberación y revocación.')
        finally:
            async with AsyncSessionLocal() as db:
                if project_id:
                    await db.execute(delete(Project).where(Project.id == UUID(project_id)))
                if accounts:
                    await db.execute(delete(User).where(User.id.in_([UUID(a['id']) for a in accounts])))
                await db.commit()
            await engine.dispose()
            print('Datos temporales eliminados por sus identificadores exactos.')


if __name__ == '__main__':
    asyncio.run(main())
