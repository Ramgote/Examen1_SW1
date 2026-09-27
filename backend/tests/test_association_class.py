import unittest
from pathlib import Path
from uuid import uuid4
from lxml import etree
from pydantic import ValidationError
from app.schemas.uml import UMLCanvasDiagram
from app.services.xmi.parser import parse_xmi, kind, local, xattr
from app.services.xmi.serializer import serialize_xmi
from app.services.xmi.ea_serializer import serialize_ea_xmi
from app.services.xmi.common import XMIError
from app.services.websocket.reservations import affected_classes
from db_case import PostgresCase


def example():
    return UMLCanvasDiagram.model_validate({'nodes': [
        {'id': 'pedido', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'Pedido'}},
        {'id': 'producto', 'position': {'x': 500, 'y': 0}, 'data': {'name': 'Producto'}},
        {'id': 'detalle', 'position': {'x': 250, 'y': 200}, 'data': {'name': 'DetallePedido',
            'attributes': [{'name': 'cantidad', 'type': 'Integer'}, {'name': 'precioUnitario', 'type': 'Double'}]}}
    ], 'edges': [{'id': 'rel', 'source': 'pedido', 'target': 'producto',
        'type': 'association_class', 'association_node_id': 'detalle',
        'source_cardinality': '1..*', 'target_cardinality': '*', 'relation_name': 'contiene'}]})


class AssociationClassTests(unittest.TestCase):
    def assert_ea_visual_association_class(self, raw):
        root = etree.fromstring(raw)
        ea = next(e for e in root if local(e) == 'Extension' and e.get('extender') == 'Enterprise Architect')
        classifier = next(e for e in root.iter('packagedElement') if kind(e) == 'AssociationClass')
        class_id = xattr(classifier, 'id')
        element = next(e for e in ea.findall('elements/element') if xattr(e, 'idref') == class_id)
        self.assertEqual(kind(element), 'Class')
        self.assertEqual(element.find('properties').get('sType'), 'Class')
        connector_id = element.find('extendedProperties').get('conID')
        self.assertNotEqual(class_id, connector_id)
        connector = next(e for e in ea.findall('connectors/connector') if xattr(e, 'idref') == connector_id)
        self.assertEqual(connector.find('properties').get('ea_type'), 'Association')
        self.assertEqual(connector.find('properties').get('subtype'), 'Class')
        self.assertEqual(connector.find('extendedProperties').get('associationclass'), class_id)
        objects = ea.findall('diagrams/diagram/elements/element')
        subjects = [e.get('subject') for e in objects]
        self.assertEqual(len(subjects), len(set(subjects)))
        self.assertIn('Left=', next(e.get('geometry') for e in objects if e.get('subject') == class_id))
        self.assertNotIn('Left=', next(e.get('geometry') for e in objects if e.get('subject') == connector_id))

    def test_export_uses_native_ea_visual_class_connector_links(self):
        fixtures = Path(__file__).parent / 'fixtures'
        # Assert the same structural contract against EA's actual export first.
        self.assert_ea_visual_association_class((fixtures / 'ea17-venta-association-class.xmi').read_bytes())
        broken = (fixtures / 'platform-association-class-broken-ea17.xmi').read_bytes()
        model, _ = parse_xmi(broken)
        project = uuid4()
        raw = serialize_ea_xmi(model, project)
        self.assert_ea_visual_association_class(raw)
        self.assertEqual(raw, serialize_ea_xmi(model, project))
        restored, _ = parse_xmi(raw)
        self.assertEqual(model.nodes, restored.nodes)
        self.assertEqual(model.edges, restored.edges)
        # Without platform metadata, the one UML classifier still defines
        # the class and association; EA-only connector metadata adds no edge.
        root = etree.fromstring(raw)
        for ext in list(root):
            if local(ext) == 'Extension' and ext.get('extender') == 'UMLPlatform':
                root.remove(ext)
        restored, _ = parse_xmi(etree.tostring(root))
        self.assertEqual(len(restored.nodes), 4)
        self.assertEqual(len(restored.edges), 2)
        detail = next(n for n in restored.nodes if n.data.name == 'DetallePedido')
        edge = next(e for e in restored.edges if e.type.value == 'association_class')
        self.assertEqual(edge.association_node_id, detail.id)

    def test_legacy_association_class_gets_visual_rectangle(self):
        model = example().model_dump(mode='json')
        model['nodes'] = model['nodes'][:2]
        model['edges'][0]['association_node_id'] = None
        raw = serialize_ea_xmi(UMLCanvasDiagram.model_validate(model), uuid4())
        self.assert_ea_visual_association_class(raw)

    def test_real_ea17_file_real_metadata_repairs_unlimited_natural(self):
        raw = (Path(__file__).parent / 'fixtures/ea17-venta-association-class.xmi').read_bytes()
        model, warnings = parse_xmi(raw)
        self.assertEqual(len(model.nodes), 4)
        self.assertEqual(len(model.edges), 2)
        detail = next(n for n in model.nodes if n.data.name == 'DetallePedido')
        self.assertEqual([(a.name, a.type) for a in detail.data.attributes],
                         [('cantitdad', 'Integer'), ('precioUnitario', 'Double')])
        edge = next(e for e in model.edges if e.type.value == 'association_class')
        self.assertEqual(edge.association_node_id, detail.id)
        names = {n.id: n.data.name for n in model.nodes}
        self.assertEqual((names[edge.source], names[edge.target]), ('Pedido', 'Producto'))
        self.assertEqual((edge.source_cardinality, edge.target_cardinality), ('1', '1'))
        self.assertEqual((detail.position.x, detail.position.y), (538, 194))
        self.assertTrue(any('precioUnitario' in w and 'UnlimitedNatural' in w for w in warnings))
        for export in (serialize_xmi, lambda m: serialize_ea_xmi(m, uuid4())):
            restored, _ = parse_xmi(export(model))
            self.assertEqual(len(restored.nodes), 4)
            self.assertEqual(len(restored.edges), 2)
            linked = next(e.association_node_id for e in restored.edges if e.type.value == 'association_class')
            self.assertEqual(next(n.data.name for n in restored.nodes if n.id == linked), 'DetallePedido')

    def test_real_repair_requires_known_href_and_explicit_metadata(self):
        raw = (Path(__file__).parent / 'fixtures/ea17-venta-association-class.xmi').read_bytes()
        for changed in (
            raw.replace(b'properties type="Real"', b'properties type="UnlimitedNatural"'),
            raw.replace(b'http://schema.omg.org/spec/UML/2.1/uml.xml#UnlimitedNatural', b'https://example.invalid/model#UnlimitedNatural'),
            raw.replace(b'extender="Enterprise Architect"', b'extender="Other"'),
        ):
            with self.assertRaises(XMIError):
                parse_xmi(changed)
        # A supported UML type remains authoritative, not silently overridden.
        changed = raw.replace(b'uml.xml#UnlimitedNatural', b'uml.xml#Integer')
        model, warnings = parse_xmi(changed)
        detail = next(n for n in model.nodes if n.data.name == 'DetallePedido')
        self.assertEqual(detail.data.attributes[1].type, 'Integer')
        self.assertFalse(any('se importa como Double' in w for w in warnings))

    def test_independent_uml21_class_owned_ends_fixture(self):
        model, _ = parse_xmi((Path(__file__).parent / 'fixtures/association-class-uml21.xmi').read_bytes())
        self.assertEqual(len(model.nodes), 3)
        edge = model.edges[0]
        linked = next(n for n in model.nodes if n.id == edge.association_node_id)
        self.assertEqual(linked.data.name, 'DetallePedido')
        self.assertEqual([a.type for a in linked.data.attributes], ['Integer', 'Double'])
        self.assertEqual((edge.source_cardinality, edge.target_cardinality), ('1..*', '*'))

    def test_exchange_single_classifier_with_attributes_and_link(self):
        for exporter in (serialize_xmi, lambda m: serialize_ea_xmi(m, uuid4())):
            raw = exporter(example())
            root = etree.fromstring(raw)
            semantic = [e for e in root.iter() if local(e) == 'packagedElement' and kind(e) == 'AssociationClass']
            self.assertEqual(len(semantic), 1)
            self.assertEqual(semantic[0].get('name'), 'DetallePedido')
            restored, _ = parse_xmi(raw)
            self.assertEqual(len(restored.nodes), 3)
            self.assertEqual(restored.edges[0].association_node_id, 'detalle')
            self.assertEqual(restored.edges[0].relation_name, 'contiene')
            # Mimic a third-party UML 2.1 export: no platform metadata, Real primitive.
            for ext in list(root):
                if local(ext) == 'Extension' and ext.get('extender') == 'UMLPlatform':
                    root.remove(ext)
            for element in root.iter():
                if kind(element) == 'PrimitiveType' and element.get('name') == 'Double':
                    element.set('name', 'Real')
            restored, _ = parse_xmi(etree.tostring(root))
            edge = restored.edges[0]
            node = next(n for n in restored.nodes if n.id == edge.association_node_id)
            self.assertEqual(node.data.name, 'DetallePedido')
            self.assertEqual([a.type for a in node.data.attributes], ['Integer', 'Double'])
            self.assertEqual(edge.source_cardinality, '1..*')
            self.assertEqual(edge.target_cardinality, '*')
            ids = [xattr(e, 'id') for e in root.iter() if xattr(e, 'id')]
            self.assertEqual(len(ids), len(set(ids)))

    def test_invalid_links_and_legacy_recovery(self):
        data = example().model_dump(mode='json')
        for linked in ('missing', 'pedido'):
            data['edges'][0]['association_node_id'] = linked
            with self.assertRaises(ValidationError): UMLCanvasDiagram.model_validate(data)
        data['edges'][0].pop('association_node_id')
        data['edges'][0]['relation_name'] = 'DetallePedido'
        restored = UMLCanvasDiagram.model_validate(data)
        self.assertEqual(restored.edges[0].association_node_id, 'detalle')

    def test_reservation_covers_linked_class(self):
        before = example().model_dump(mode='json')
        after = example().model_dump(mode='json')
        after['edges'][0]['target_cardinality'] = '1'
        self.assertEqual(affected_classes(before, after), {'pedido', 'producto', 'detalle'})


class AssociationClassAPITests(PostgresCase):
    async def test_save_reload_rename_and_export(self):
        _, token = await self.account('association')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Association test'})
        path = '/projects/' + project['id']
        saved = await self.request('PUT', path + '/canvas', 200, token, example().model_dump(mode='json'))
        saved['nodes'][2]['data']['name'] = 'LineaPedido'
        saved = await self.request('PUT', path + '/canvas', 200, token, saved)
        reloaded = await self.request('GET', path + '/canvas', 200, token)
        self.assertEqual(reloaded['edges'][0]['association_node_id'], 'detalle')
        self.assertEqual(reloaded['nodes'][2]['data']['name'], 'LineaPedido')
        response = await self.client.get('/api/v1' + path + '/xmi?format=ea17',
            headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.status_code, 200)
        preview = await self.client.post('/api/v1' + path + '/xmi/preview', content=response.content,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/xml'})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['summary']['classes'], 3)
        self.assertEqual(preview.json()['document']['edges'][0]['association_node_id'], 'detalle')
        raw = (Path(__file__).parent / 'fixtures/ea17-venta-association-class.xmi').read_bytes()
        preview = await self.client.post('/api/v1' + path + '/xmi/preview', content=raw,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/xml'})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['summary']['classes'], 4)
        self.assertEqual(preview.json()['summary']['relationships'], 2)
        self.assertEqual(reloaded, await self.request('GET', path + '/canvas', 200, token))
