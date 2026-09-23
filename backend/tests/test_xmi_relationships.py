import unittest
from uuid import uuid4
from lxml import etree
from app.schemas.uml import UMLCanvasDiagram
from app.services.xmi.serializer import serialize_xmi
from app.services.xmi.ea_serializer import serialize_ea_xmi
from app.services.xmi.parser import parse_xmi, kind, xattr, local
from app.services.xmi.common import XMIError, XMI, tag
from db_case import PostgresCase


def model(relation='template_binding'):
    return UMLCanvasDiagram.model_validate({'nodes': [
        {'id': 'a', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'Cliente'}},
        {'id': 'b', 'position': {'x': 300, 'y': 0}, 'data': {'name': 'Repositorio',
            'template_parameters': ['T'] if relation == 'template_binding' else [],
            'attributes': [{'name': 'valor', 'type': 'T'}] if relation == 'template_binding' else []}},
    ], 'edges': [{'id': 'rel', 'source': 'a', 'target': 'b', 'type': relation,
                 'relation_name': 'Ejemplo',
                 'template_arguments': {'T': 'String'} if relation == 'template_binding' else {}}]})


class RelationshipXMITests(unittest.TestCase):
    def test_new_relationships_keep_native_types_standard_and_ea(self):
        for relation, native in [('realization', 'Realization'), ('association_class', 'AssociationClass'), ('template_binding', 'TemplateBinding')]:
            original = model(relation)
            for raw in (serialize_xmi(original), serialize_ea_xmi(original, uuid4(), 'Prueba EA')):
                with self.subTest(relation=relation, ea=b'EAID' in raw):
                    root = etree.fromstring(raw)
                    self.assertEqual(sum(kind(e) == native for e in root.iter() if local(e) != 'element'), 1)
                    restored, _ = parse_xmi(raw)
                    self.assertEqual(restored.edges[0].type.value, relation)
                    self.assertEqual(restored.edges[0].template_arguments, original.edges[0].template_arguments)
                    self.assertEqual(restored.edges[0].relation_name, 'Ejemplo')
                    self.assertEqual(len(restored.nodes), 2)
                    # Prove types come from UML, not just our canvas extension.
                    for ext in list(root):
                        if local(ext) == 'Extension': root.remove(ext)
                    without_extension, _ = parse_xmi(etree.tostring(root))
                    self.assertEqual(without_extension.edges[0].type.value, relation)
                    self.assertEqual(without_extension.nodes[1].data.template_parameters, original.nodes[1].data.template_parameters)
                    self.assertEqual(without_extension.edges[0].template_arguments, original.edges[0].template_arguments)

    def test_ea_template_references_resolve(self):
        root = etree.fromstring(serialize_ea_xmi(model(), uuid4(), 'Plantilla'))
        ids = {xattr(e, 'id') for e in root.iter() if xattr(e, 'id')}
        for element in root.iter():
            for field in ('signature', 'formal', 'actual', 'parameteredElement'):
                if element.get(field): self.assertIn(element.get(field), ids)

    def test_incomplete_binding_export_and_unresolved_import_are_rejected(self):
        doc = model().model_copy(deep=True)
        doc.edges[0].template_arguments = {}
        with self.assertRaisesRegex(XMIError, 'sustituci'): serialize_xmi(doc)
        raw = serialize_xmi(model()).replace(b'signature="ts_b"', b'signature="missing"')
        with self.assertRaisesRegex(XMIError, 'firma'): parse_xmi(raw)
        raw = serialize_xmi(model()).replace(b'formal="tp_b_0"', b'formal="missing"')
        with self.assertRaisesRegex(XMIError, 'parámetro'): parse_xmi(raw)

    def test_association_class_members_are_not_silently_dropped(self):
        root = etree.fromstring(serialize_xmi(model('association_class')))
        assoc = next(e for e in root.iter() if kind(e) == 'AssociationClass')
        etree.SubElement(assoc, 'ownedOperation', {tag(XMI, 'id'): 'operation', 'name': 'calcular'})
        with self.assertRaisesRegex(XMIError, 'pérdida'): parse_xmi(etree.tostring(root))

    def test_nested_interface_realization_is_imported(self):
        root = etree.fromstring(serialize_xmi(model('realization')))
        rel = next(e for e in root.iter() if kind(e) == 'Realization')
        source = next(e for e in root.iter() if xattr(e, 'id') == 'n_a')
        rel.getparent().remove(rel)
        source.append(rel)
        rel.tag = 'interfaceRealization'
        rel.set(tag(XMI, 'type'), 'uml:InterfaceRealization')
        rel.attrib.pop('client'); rel.attrib.pop('supplier')
        rel.set('contract', 'n_b')
        restored, _ = parse_xmi(etree.tostring(root))
        self.assertEqual(restored.edges[0].type.value, 'realization')


class RelationshipXMIAPITests(PostgresCase):
    async def test_incomplete_template_export_returns_actionable_422(self):
        _, token = await self.account('binding')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Binding export'})
        path = '/projects/' + project['id']
        doc = model().model_dump(mode='json')
        doc['edges'][0]['template_arguments'] = {}
        await self.request('PUT', path + '/canvas', 200, token, doc)
        response = await self.request('GET', path + '/xmi', 422, token)
        self.assertIn('sustitución', response['detail'])
