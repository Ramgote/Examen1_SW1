import copy
import json
from io import BytesIO
from zipfile import ZipFile
import unittest
from app.schemas.uml import UMLCanvasDiagram
from app.services.generator.packager import generate_solution
from app.services.generator.ast_transformer import GenerationError
from test_sprint5 import example
from db_case import PostgresCase


def workshop():
    data = example()
    data['nodes'][1]['data'].update(name='Vehiculo', attributes=[
        {'name': 'matricula', 'type': 'String', 'is_nullable': False}])
    data['edges'][0]['target_role'] = 'vehiculos'
    data['nodes'].append({'id': 'reparacion', 'position': {'x': 600, 'y': 0},
        'data': {'name': 'Reparacion', 'attributes': [
            {'name': 'descripcion', 'type': 'String', 'is_nullable': False}]}})
    data['edges'].append({'id': 'vehiculo-reparacion', 'source': 'pedido', 'target': 'reparacion',
        'source_cardinality': '1', 'target_cardinality': '*',
        'source_role': 'vehiculo', 'target_role': 'reparaciones'})
    return data


class SolutionTests(unittest.TestCase):
    def test_two_domains_same_snapshot_portable_files(self):
        for data in (example(), workshop()):
            model = UMLCanvasDiagram.model_validate(dict(data, version=7))
            before = model.model_dump()
            raw, _ = generate_solution(model, 'project-a')
            self.assertEqual(before, model.model_dump())
            with ZipFile(BytesIO(raw)) as archive:
                contract = json.loads(archive.read('backend/mobile-contract.json'))
                self.assertEqual(contract, json.loads(archive.read('mobile/assets/mobile-contract.json')))
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['canvas_version'], 7)
                self.assertEqual(manifest['contract_fingerprint'], contract['fingerprint'])
                self.assertTrue(archive.read('mobile/android/gradle/wrapper/gradle-wrapper.jar').startswith(b'PK'))
                domain = archive.read('mobile/lib/generated/domain.dart').decode()
                for entity in contract['entities']:
                    self.assertIn('class Generated' + entity['name'] + 'Service', domain)
                for path in archive.namelist():
                    self.assertNotIn('local.properties', path)
                    self.assertNotIn('.env', path)
                    self.assertNotIn('/build/', path)
                    self.assertNotIn('.dart_tool', path)
                    if path.endswith(('.dart', '.kts', '.properties')):
                        self.assertNotIn(b'192.168.1.51', archive.read(path))

    def test_project_identity_and_contract_changes(self):
        def extract(data, project):
            raw, _ = generate_solution(UMLCanvasDiagram.model_validate(data), project)
            with ZipFile(BytesIO(raw)) as z:
                return (z.read('mobile/android/app/build.gradle.kts'),
                        json.loads(z.read('mobile/assets/mobile-contract.json'))['fingerprint'])
        original = example()
        changed = copy.deepcopy(original)
        changed['nodes'][0]['data']['attributes'].append({'name': 'telefono', 'type': 'String'})
        a, b, c = extract(original, 'a'), extract(changed, 'a'), extract(original, 'b')
        self.assertEqual(a[0], b[0])
        self.assertNotEqual(a[1], b[1])
        self.assertNotEqual(a[0], c[0])

    def test_invalid_model_fails_whole_generation(self):
        with self.assertRaises(GenerationError):
            generate_solution(UMLCanvasDiagram())
        data = example()
        data['edges'] = []
        for node in data['nodes']:
            node['data']['is_abstract'] = True
        with self.assertRaises(GenerationError):
            generate_solution(UMLCanvasDiagram.model_validate(data))


class SolutionAPITests(PostgresCase):
    async def test_access_version_and_no_canvas_writes(self):
        _, token = await self.account('owner')
        viewer, vt = await self.account('viewer')
        _, outsider = await self.account('outsider')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Solution test'})
        path = '/projects/' + project['id']
        await self.request('PUT', path + '/members', 200, token, {'email': viewer['email'], 'role': 'VIEWER'})
        payload = {'expected_version': 1}
        for suffix in ('', '/validate'):
            await self.request('POST', path + '/generate/solution' + suffix, 401, body=payload)
            await self.request('POST', path + '/generate/solution' + suffix, 404, outsider, payload)
        result = await self.request('POST', path + '/generate/solution/validate', 200, token, payload)
        self.assertFalse(result['valid'])
        await self.request('POST', path + '/generate/solution', 422, token, payload)
        saved = await self.request('PUT', path + '/canvas', 200, token, dict(example(), version=1))
        await self.request('POST', path + '/generate/solution', 409, token, payload)
        payload['expected_version'] = saved['version']
        result = await self.request('POST', path + '/generate/solution/validate', 200, vt, payload)
        self.assertTrue(result['valid'])
        response = await self.client.post('/api/v1' + path + '/generate/solution', json=payload,
            headers={'Authorization': 'Bearer ' + vt})
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as archive:
            self.assertIn('mobile/pubspec.yaml', archive.namelist())
        self.assertEqual(saved, await self.request('GET', path + '/canvas', 200, token))
