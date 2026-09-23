import copy
from io import BytesIO
from zipfile import ZipFile
import unittest
from app.schemas.uml import UMLCanvasDiagram
from app.services.generator.ast_transformer import transform, GenerationError
from app.services.generator.packager import generate_spring
from app.services.generator.spring_boot.renderer import render
from db_case import PostgresCase


def example():
    return {'nodes': [
        {'id': 'cliente', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'Cliente', 'attributes': [
            {'name': 'nombre', 'type': 'String', 'is_nullable': False, 'is_unique': True}]}},
        {'id': 'pedido', 'position': {'x': 300, 'y': 0}, 'data': {'name': 'Pedido', 'attributes': [
            {'name': 'total', 'type': 'BigDecimal', 'is_nullable': False}]}},
    ], 'edges': [{'id': 'cliente-pedido', 'source': 'cliente', 'target': 'pedido',
                   'source_cardinality': '1', 'target_cardinality': '0..*',
                   'source_role': 'cliente', 'target_role': 'pedidos'}]}


class GeneratorTests(unittest.TestCase):
    def test_archive_and_original_model_not_mutated(self):
        model = UMLCanvasDiagram.model_validate(example())
        before = model.model_dump()
        raw, warnings = generate_spring(model)
        self.assertEqual(model.model_dump(), before)
        self.assertEqual(len(warnings), 2)
        with ZipFile(BytesIO(raw)) as archive:
            self.assertIn('pom.xml', archive.namelist())
            self.assertIn('model.json', archive.namelist())
            self.assertNotIn('.env', archive.namelist())
            for path in archive.namelist():
                self.assertNotIn('..', path)
                self.assertFalse(path.startswith('/'))
            request = archive.read('src/main/java/com/generated/dto/PedidoRequest.java').decode()
            self.assertIn('@NotNull Long clienteId', request)
            self.assertNotIn('Long id,', request)

    def test_bidirectional_mappings_and_composition_direction(self):
        for source, target, kind, expected in [('1', '*', 'association', ('OneToMany', 'ManyToOne')),
            ('*', '1', 'association', ('ManyToOne', 'OneToMany')),
            ('*', '*', 'association', ('ManyToMany', 'ManyToMany')),
            ('0..1', '1', 'association', ('OneToOne', 'OneToOne')),
            ('1', '*', 'composition', ('OneToMany', 'ManyToOne'))]:
            with self.subTest(source=source, target=target, kind=kind):
                data = example(); data['edges'][0].update(type=kind, source_cardinality=source, target_cardinality=target)
                plan = transform(UMLCanvasDiagram.model_validate(data))
                rels = [c['rels'][0] for c in plan['classes']]
                self.assertEqual(tuple(r['kind'] for r in rels), expected)
                self.assertEqual(sum(r['owner'] for r in rels), 1)
                files, _ = render(UMLCanvasDiagram.model_validate(data))
                self.assertEqual('CascadeType.REMOVE' in files['src/main/java/com/generated/entity/Cliente.java'], kind == 'composition')
                self.assertNotIn('CascadeType.REMOVE', files['src/main/java/com/generated/entity/Pedido.java'])

    def test_inheritance_pk_and_attributes(self):
        data = example(); data['edges'] = [{'id': 'extends', 'source': 'pedido', 'target': 'cliente', 'type': 'generalization'}]
        data['nodes'][0]['data']['is_abstract'] = True
        plan = transform(UMLCanvasDiagram.model_validate(data))
        child = plan['classes'][1]
        self.assertEqual([a['name'] for a in child['all_attrs']], ['id', 'nombre', 'total'])
        files, _ = render(UMLCanvasDiagram.model_validate(data))
        self.assertNotIn('src/main/java/com/generated/api/ClienteController.java', files)
        self.assertIn('extends Cliente', files['src/main/java/com/generated/entity/Pedido.java'])

    def test_explicit_pk_is_assigned_and_immutable(self):
        data = example(); data['nodes'][0]['data']['attributes'].append({'name': 'codigo', 'type': 'String', 'is_pk': True})
        files, _ = render(UMLCanvasDiagram.model_validate(data))
        self.assertIn('String clienteId', files['src/main/java/com/generated/dto/PedidoRequest.java'])
        self.assertIn('La PK es inmutable', files['src/main/java/com/generated/service/ClienteService.java'])

    def test_unsupported_models_are_rejected(self):
        variants = []
        def invalid(mutate):
            data = example(); mutate(data); variants.append(data)
        invalid(lambda d: d['nodes'][0]['data']['attributes'][0].update(name='class'))
        invalid(lambda d: d['nodes'][0]['data']['attributes'][0].update(default_value='"; System.exit(0);'))
        invalid(lambda d: d['nodes'][0]['data']['attributes'][0].update(is_static=True))
        invalid(lambda d: d['nodes'][0]['data']['attributes'][0].update(type='Pedido'))
        invalid(lambda d: d['edges'][0].update(target_role='nombre'))
        invalid(lambda d: d['edges'][0].update(target_role='get'))
        invalid(lambda d: d['edges'][0].update(target_cardinality='2..9999999999'))
        invalid(lambda d: d['nodes'][0]['data']['attributes'].extend([
            {'name': 'keyOne', 'type': 'Long', 'is_pk': True}, {'name': 'keyTwo', 'type': 'Long', 'is_pk': True}]))
        for data in variants:
            with self.subTest(data=data):
                with self.assertRaises(GenerationError): transform(UMLCanvasDiagram.model_validate(data))
        with self.assertRaises(GenerationError): transform(UMLCanvasDiagram())

    def test_self_association_requires_distinct_roles_and_composition_cycles_rejected(self):
        data = example(); data['edges'][0].update(target='cliente', source_role='padre', target_role='hijos')
        transform(UMLCanvasDiagram.model_validate(data))
        data['edges'][0].update(type='composition')
        with self.assertRaises(GenerationError): transform(UMLCanvasDiagram.model_validate(data))


class GenerationAPITests(PostgresCase):
    async def test_permissions_validation_download_and_version_without_writes(self):
        owner, token = await self.account('owner')
        viewer, viewer_token = await self.account('viewer')
        _, outsider_token = await self.account('outsider')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Generation test'})
        path = '/projects/' + project['id']
        await self.request('PUT', path + '/members', 200, token, {'email': viewer['email'], 'role': 'VIEWER'})
        payload = {'expected_version': 1}
        await self.request('POST', path + '/generate/spring/validate', 401, body=payload)
        await self.request('POST', path + '/generate/spring/validate', 404, outsider_token, payload)
        empty = await self.request('POST', path + '/generate/spring/validate', 200, token, payload)
        self.assertFalse(empty['valid'])
        await self.request('POST', path + '/generate/spring', 422, token, payload)
        saved = await self.request('PUT', path + '/canvas', 200, token, dict(example(), version=1))
        await self.request('POST', path + '/generate/spring/validate', 409, token, payload)
        payload['expected_version'] = saved['version']
        valid = await self.request('POST', path + '/generate/spring/validate', 200, viewer_token, payload)
        self.assertTrue(valid['valid'])
        response = await self.client.post('/api/v1' + path + '/generate/spring', json=payload,
                                         headers={'Authorization': 'Bearer ' + viewer_token})
        self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
        self.assertEqual(response.headers['content-type'], 'application/zip')
        with ZipFile(BytesIO(response.content)) as archive: self.assertIn('pom.xml', archive.namelist())
        after = await self.request('GET', path + '/canvas', 200, token)
        self.assertEqual(after, saved)


if __name__ == '__main__':
    unittest.main()
