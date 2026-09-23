import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from uuid import uuid4, UUID
from lxml import etree
from fastapi import HTTPException
from app.services.websocket.reservations import Reservations, affected_classes
from app.services.websocket.connection_manager import manager, ConnectionManager, Peer
from app.services.websocket.events import ReservationEvent, Update
from app.services.xmi.ea_serializer import serialize_ea_xmi, EA_XMI
from app.services.xmi.common import tag
from app.services.xmi.parser import parse_xmi
from app.schemas.uml import UMLCanvasDiagram
from db_case import PostgresCase
from test_sprint2 import example


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.leases = Reservations()
        self.first = SimpleNamespace(id='session-a', name='Ana')
        self.second = SimpleNamespace(id='session-b', name='Ana')

    def test_atomic_batch_distinct_sessions_and_release(self):
        self.leases.acquire('p', ['a'], self.first)
        with self.assertRaises(HTTPException) as error:
            self.leases.acquire('p', ['b', 'a'], self.second)
        self.assertEqual(error.exception.status_code, 423)
        self.assertNotIn(('p', 'b'), self.leases.items)
        self.leases.release('p', self.second.id)
        self.assertEqual(len(self.leases.public('p')), 1)
        self.leases.release('p', self.first.id)
        self.leases.acquire('p', ['a'], self.second)
        self.leases.acquire('other-project', ['a'], self.first)

    def test_expiry_heartbeat_does_not_resurrect_and_public_has_no_clock(self):
        with patch('app.services.websocket.reservations.monotonic', return_value=0):
            self.leases.acquire('p', ['a'], self.first)
            self.assertNotIn('expires', self.leases.public('p')[0])
        with patch('app.services.websocket.reservations.monotonic', return_value=30):
            self.leases.renew('p', self.first.id)
        with patch('app.services.websocket.reservations.monotonic', return_value=76):
            self.leases.renew('p', self.first.id)
            self.assertEqual(self.leases.public('p'), [])
            self.leases.acquire('p', ['a'], self.second)

    def test_relationship_retarget_delete_and_class_changes(self):
        before = example()
        after = copy.deepcopy(before)
        after['edges'] = []
        self.assertEqual(affected_classes(before, after), {'client', 'order'})
        after = copy.deepcopy(before)
        after['nodes'][0]['position']['x'] += 1
        self.assertEqual(affected_classes(before, after), {'client'})
        after = copy.deepcopy(before)
        after['edges'][0]['target'] = 'new'
        self.assertEqual(affected_classes(before, after), {'client', 'order', 'new'})

    def test_ea17_positions_without_platform_extension_and_invalid_geometry(self):
        raw = serialize_ea_xmi(UMLCanvasDiagram.model_validate(example()), uuid4())
        root = etree.fromstring(raw)
        for ext in list(root.findall(tag(EA_XMI, 'Extension'))):
            if ext.get('extender') == 'UMLPlatform':
                root.remove(ext)
        item = root.find('.//diagrams/diagram/elements/element')
        item.set('geometry', 'Left=720;Top=120;Right=980;Bottom=300;')
        parsed, warnings = parse_xmi(etree.tostring(root))
        self.assertEqual(parsed.nodes[0].position.x, 720)
        self.assertEqual(parsed.nodes[0].position.y, 120)
        self.assertEqual(len(parsed.edges), len(example()['edges']))
        item.set('geometry', 'Left=nan;Top=20;')
        parsed, warnings = parse_xmi(etree.tostring(root))
        self.assertTrue(any('inválida' in w for w in warnings))
        self.assertEqual(parsed.nodes[0].position.x, 60)


class ManagerReservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_concurrent_requests_only_one_wins(self):
        import asyncio
        room = ConnectionManager()
        project = uuid4()
        peers = [Peer(socket=SimpleNamespace(send_json=AsyncMock()), project_id=project, token='test') for _ in range(2)]
        event = ReservationEvent(type='reserve', op_id=uuid4(), node_ids=['class'])
        with patch('app.services.websocket.connection_manager.authorize', new_callable=AsyncMock), patch.object(room, '_refresh', new_callable=AsyncMock):
            results = await asyncio.gather(*(room.reserve(p, event) for p in peers), return_exceptions=True)
        self.assertEqual(sum(isinstance(r, HTTPException) and r.status_code == 423 for r in results), 1)
        self.assertEqual(len(room.reservations.public(project)), 1)


class ReservationAPITests(PostgresCase):
    async def test_http_apply_rejects_foreign_reservation_including_relations(self):
        owner, token = await self.account('lock-owner')
        editor, editor_token = await self.account('lock-editor')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Reservations'})
        pid = UUID(project['id']); path = '/projects/' + project['id']
        await self.request('PUT', path + '/members', 200, token, {'email': editor['email'], 'role': 'EDITOR'})
        saved = await self.request('PUT', path + '/canvas', 200, token, example())
        peer = Peer(socket=None, project_id=pid, token=token, user_id=owner['id'], name='Owner', role='OWNER')
        manager.rooms[pid] = {peer}
        manager.reservations.acquire(pid, ['client'], peer)
        try:
            for change in ('name', 'delete', 'relation'):
                draft = copy.deepcopy(saved)
                if change == 'name': draft['nodes'][0]['data']['name'] = 'Persona'
                elif change == 'delete': draft['nodes'] = []; draft['edges'] = []
                else: draft['edges'] = []
                await self.request('PUT', path + '/canvas', 423, editor_token, draft)
            draft = copy.deepcopy(saved); draft['nodes'][0]['data']['name'] = 'Persona'
            # Guessing another user's public connection id must not bypass the lock.
            headers = {'Authorization': 'Bearer ' + editor_token, 'X-Collaboration-Session': peer.id}
            response = await self.client.put('/api/v1' + path + '/canvas', headers=headers, json=draft)
            self.assertEqual(response.status_code, 423)
            self.assertEqual(await self.request('GET', path + '/canvas', 200, token), saved)
            headers['Authorization'] = 'Bearer ' + token
            response = await self.client.put('/api/v1' + path + '/canvas', headers=headers, json=draft)
            self.assertEqual(response.status_code, 200, response.text)
            exported = await self.client.get('/api/v1' + path + '/xmi?format=ea17', headers=headers)
            self.assertEqual(exported.status_code, 200)
            self.assertIn('-ea17.xmi', exported.headers['content-disposition'])
            self.assertEqual(len(parse_xmi(exported.content)[0].nodes), 2)
        finally:
            manager.rooms.pop(pid, None)
            manager.reservations.release(pid, peer.id)
