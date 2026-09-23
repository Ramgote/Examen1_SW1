import copy
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.schemas.uml import UMLCanvasDiagram
from app.core.database import get_db
from app.core.security import create_token
from main import app
from db_case import PostgresCase


def example():
    return {'version': 1, 'nodes': [
        {'id': 'client', 'position': {'x': 12, 'y': 34}, 'data': {
            'name': 'Cliente', 'attributes': [{'name': 'nombre', 'type': 'String'}],
            'methods': [{'name': 'saludar', 'return_type': 'String', 'parameters': [{'name': 'prefijo', 'param_type': 'String'}]}]}},
        {'id': 'order', 'position': {'x': 400, 'y': 34}, 'data': {'name': 'Pedido'}},
    ], 'edges': [{'id': 'rel1', 'source': 'client', 'target': 'order', 'type': 'association',
                   'source_cardinality': '1', 'target_cardinality': '0..*'}],
        'metadata': {'viewport': {'x': 5, 'y': 10, 'zoom': 1.25}}}


class UMLValidationTests(unittest.TestCase):
    def test_valid_document_and_custom_type(self):
        payload = example()
        payload['nodes'][1]['data']['attributes'] = [{'name': 'cliente', 'type': 'Cliente'}]
        self.assertEqual(UMLCanvasDiagram.model_validate(payload).nodes[1].data.attributes[0].type, 'Cliente')

    def test_invalid_documents(self):
        cases = []
        def invalid(label, mutate):
            data = example(); mutate(data); cases.append((label, data))
        invalid('duplicate ids', lambda d: d['nodes'].append(copy.deepcopy(d['nodes'][0])))
        invalid('missing target', lambda d: d['edges'][0].update(target='missing'))
        invalid('unknown type', lambda d: d['nodes'][0]['data']['attributes'][0].update(type='Imaginary'))
        invalid('invalid attribute name', lambda d: d['nodes'][0]['data']['attributes'][0].update(name='not valid'))
        invalid('duplicate class', lambda d: d['nodes'][1]['data'].update(name='Cliente'))
        invalid('duplicate attribute', lambda d: d['nodes'][0]['data']['attributes'].append({'name': 'nombre'}))
        invalid('duplicate method', lambda d: d['nodes'][0]['data']['methods'].append(copy.deepcopy(d['nodes'][0]['data']['methods'][0])))
        invalid('abstract method', lambda d: d['nodes'][0]['data']['methods'][0].update(is_abstract=True))
        invalid('multiplicity bounds', lambda d: d['edges'][0].update(target_cardinality='5..2'))
        invalid('multiplicity syntax', lambda d: d['edges'][0].update(target_cardinality='N'))
        invalid('unbounded lower multiplicity', lambda d: d['edges'][0].update(target_cardinality='*..*'))
        invalid('composition owner multiplicity', lambda d: d['edges'][0].update(type='composition', source_cardinality='*'))
        invalid('self inheritance', lambda d: d['edges'][0].update(type='generalization', target='client'))
        invalid('negative version', lambda d: d.update(version=-1))
        invalid('unknown schema', lambda d: d.update(schema_version=2))
        invalid('non finite position', lambda d: d['nodes'][0]['position'].update(x=float('inf')))
        invalid('internal UI fields', lambda d: d['nodes'][0].update(selected=True))
        for label, data in cases:
            with self.subTest(label=label), self.assertRaises(ValidationError):
                UMLCanvasDiagram.model_validate(data)

    def test_inheritance_cycle_rejected(self):
        data = example()
        data['edges'][0]['type'] = 'generalization'
        data['edges'].append({'id': 'reverse', 'source': 'order', 'target': 'client', 'type': 'generalization'})
        with self.assertRaises(ValidationError):
            UMLCanvasDiagram.model_validate(data)

    def test_recursive_association_and_composition_are_allowed(self):
        # Recursividad entre tipos no implica un ciclo entre instancias compuestas.
        for kind in ('association', 'composition'):
            data = example(); data['edges'][0].update(target='client', type=kind)
            UMLCanvasDiagram.model_validate(data)

    def test_custom_multiplicity_and_overloads(self):
        data = example(); data['edges'][0]['target_cardinality'] = '2..5'
        data['nodes'][0]['data']['methods'].append({'name': 'saludar', 'parameters': []})
        UMLCanvasDiagram.model_validate(data)

    def test_method_signature_resolves_equivalent_type_names(self):
        data = example()
        data['nodes'][0]['data']['methods'] = [
            {'name': 'agregar', 'parameters': [{'name': 'pedido', 'param_type': 'Pedido'}]},
            {'name': 'agregar', 'parameters': [{'name': 'otro', 'param_type': 'com.example.model.Pedido'}]},
        ]
        with self.assertRaises(ValidationError):
            UMLCanvasDiagram.model_validate(data)


class CommitOrderingTests(unittest.TestCase):
    def test_transaction_failure_is_not_reported_as_success(self):
        user_id = uuid4()
        db = AsyncMock()
        db.get.return_value = SimpleNamespace(id=user_id, email='transaction@example.test',
            full_name='Transaction test', is_active=True, created_at=datetime.now(timezone.utc))
        async def failing_transaction():
            yield db
            raise RuntimeError('Simulated commit failure')
        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = failing_transaction
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {create_token(user_id)}'})
            self.assertEqual(response.status_code, 500)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)


class CanvasAPITests(PostgresCase):
    async def test_persistence_roles_and_stale_version(self):
        owner, token = await self.account('owner')
        editor, editor_token = await self.account('editor')
        viewer, viewer_token = await self.account('viewer')
        _, outsider_token = await self.account('outsider')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Canvas tests'})
        base = '/projects/' + project['id']
        path = base + '/canvas'
        initial = await self.request('GET', path, 200, token)
        self.assertEqual(initial['version'], 1)
        self.assertEqual(initial['nodes'], [])
        await self.request('GET', path, 401)
        await self.request('GET', path, 404, outsider_token)
        await self.request('PUT', base + '/members', 200, token, {'email': editor['email'], 'role': 'EDITOR'})
        await self.request('PUT', base + '/members', 200, token, {'email': viewer['email'], 'role': 'VIEWER'})
        await self.request('GET', path, 200, viewer_token)
        payload = example()
        await self.request('PUT', path, 403, viewer_token, payload)
        await self.request('PUT', path, 404, outsider_token, payload)
        saved = await self.request('PUT', path, 200, editor_token, payload)
        self.assertEqual(saved['version'], 2)
        reopened = await self.request('GET', path, 200, token)
        self.assertEqual(saved, reopened)
        self.assertEqual(reopened['metadata'], payload['metadata'])
        await self.request('PUT', path, 409, token, payload)
        self.assertEqual(await self.request('GET', path, 200, token), saved)
        bad = copy.deepcopy(saved); bad['edges'][0]['target'] = 'missing'
        await self.request('PUT', path, 422, token, bad)
        self.assertEqual(await self.request('GET', path, 200, token), saved)
        saved['edges'][0]['type'] = 'composition'
        changed = await self.request('PUT', path, 200, token, saved)
        self.assertEqual(changed['version'], 3)
        await self.request('DELETE', base + '/members/' + editor['id'], 204, token)
        await self.request('PUT', path, 404, editor_token, changed)
