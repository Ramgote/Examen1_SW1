import unittest
from pathlib import Path
from uuid import uuid4
from lxml import etree
from app.schemas.uml import UMLCanvasDiagram
from app.services.xmi.common import XMI, MAX_BYTES, XMIError, tag
from app.services.xmi.serializer import serialize_xmi
from app.services.xmi.ea_serializer import serialize_ea_xmi, EA_XMI, EA_UML
from app.services.xmi.parser import parse_xmi
from db_case import PostgresCase
from test_sprint2 import example

FIXTURE = Path(__file__).parent / 'fixtures' / 'uml-exchange.xmi'
EA_FIXTURE = Path(__file__).parent / 'fixtures' / 'ea15-tienda.xmi'


class XMIUnitTests(unittest.TestCase):
    def test_ea_unlimited_bounds_pair_and_invalid_negative_bounds(self):
        for lower, upper, expected in [('-1', '-1', '*'), ('*', '*', '*'),
                                        ('0', '-1', '*'), ('1', '-1', '1..*'),
                                        ('-1', '1', None), ('-2', '-1', None), ('5', '2', None)]:
            with self.subTest(lower=lower, upper=upper):
                root = etree.fromstring(serialize_ea_xmi(UMLCanvasDiagram.model_validate(example()), uuid4()))
                end = root.xpath('.//ownedEnd')[0]
                end.find('lowerValue').set('value', lower)
                end.find('upperValue').set('value', upper)
                raw = etree.tostring(root)
                if expected is None:
                    with self.assertRaises(XMIError):
                        parse_xmi(raw)
                else:
                    parsed, _ = parse_xmi(raw)
                    self.assertEqual(parsed.edges[0].target_cardinality, expected)

    def test_scalar_uml_uniqueness_is_independent_of_database_constraint(self):
        for db_unique in (False, True):
            data = example()
            data['nodes'][0]['data']['attributes'][0]['is_unique'] = db_unique
            document = UMLCanvasDiagram.model_validate(data)
            for raw in (serialize_xmi(document), serialize_ea_xmi(document, uuid4())):
                with self.subTest(db_unique=db_unique):
                    prop = etree.fromstring(raw).xpath('.//ownedAttribute')[0]
                    self.assertEqual(prop.get('isUnique'), 'true')
                    self.assertEqual(prop.get('isOrdered'), 'false')
                    parsed, _ = parse_xmi(raw)
                    self.assertEqual(parsed.nodes[0].data.attributes[0].is_unique, db_unique)

    def test_ea_export_single_root_package_diagram_and_resolvable_references(self):
        original = UMLCanvasDiagram.model_validate(example())
        raw = serialize_ea_xmi(original, uuid4(), 'Prueba de clases')
        root = etree.fromstring(raw)
        documentation = root.findall(tag(EA_XMI, 'Documentation'))
        self.assertEqual(len(documentation), 1)
        self.assertEqual(documentation[0].get('exporter'), 'Enterprise Architect')
        self.assertEqual(documentation[0].get('exporterVersion'), '6.5')
        extensions = root.findall(tag(EA_XMI, 'Extension'))
        self.assertEqual(extensions[0].get('extender'), 'Enterprise Architect')
        self.assertEqual(extensions[1].get('generator'), 'UMLPlatform')
        model = root.find(tag(EA_UML, 'Model'))
        self.assertEqual(len(model), 1)
        self.assertEqual(model[0].get('name'), 'Modelo')
        ids = [e.get(tag(EA_XMI, 'id')) for e in root.iter() if e.get(tag(EA_XMI, 'id'))]
        self.assertEqual(len(ids), len(set(ids)))
        for element in root.iter():
            for name in (tag(EA_XMI, 'idref'), 'subject', 'general', 'client', 'supplier', 'association', 'ref'):
                if element.get(name):
                    for ref in element.get(name).split(): self.assertIn(ref, ids)
        diagrams = root.xpath(".//diagrams/diagram")
        self.assertEqual(len(diagrams), 1)
        self.assertEqual(diagrams[0].find('model').get('package'), model[0].get(tag(EA_XMI, 'id')))
        self.assertEqual(len(diagrams[0].findall('elements/element')), 3)
        parsed, _ = parse_xmi(raw)
        self.assertEqual(parsed.nodes, original.nodes)
        self.assertEqual(parsed.edges[0].target_cardinality, '*')
        self.assertEqual(root.get(tag(EA_XMI, 'version')), '2.1')

    def test_ea_ids_are_stable_per_project_and_distinct_between_projects(self):
        document = UMLCanvasDiagram.model_validate(example()); first = uuid4()
        self.assertEqual(serialize_ea_xmi(document, first), serialize_ea_xmi(document, first))
        self.assertNotEqual(serialize_ea_xmi(document, first), serialize_ea_xmi(document, uuid4()))

    def test_ea_export_relationship_types_roundtrip(self):
        for kind in ('association', 'aggregation', 'composition', 'generalization', 'dependency'):
            data = example(); data['edges'][0]['type'] = kind
            original = UMLCanvasDiagram.model_validate(data)
            parsed, _ = parse_xmi(serialize_ea_xmi(original, uuid4()))
            with self.subTest(kind=kind):
                self.assertEqual(parsed.edges[0].type.value, kind)
                self.assertEqual((parsed.edges[0].source, parsed.edges[0].target), ('client', 'order'))

    def test_ea15_real_model_types_methods_and_nested_association_references(self):
        parsed, _ = parse_xmi(EA_FIXTURE.read_bytes())
        classes = {n.data.name: n for n in parsed.nodes}
        self.assertEqual(set(classes), {'Class1', 'Cliente', 'Email', 'Telefono'})
        self.assertEqual([(a.name, a.type, a.visibility.value, a.is_nullable) for a in classes['Cliente'].data.attributes],
                         [('ci', 'Integer', '#', False), ('nombre', 'String', '#', False)])
        self.assertEqual([(m.name, m.return_type) for m in classes['Cliente'].data.methods],
                         [('editar', 'void'), ('eliminar', 'void'), ('guardar', 'void'), ('listar', 'void')])
        names = {n.id: n.data.name for n in parsed.nodes}
        relationships = {frozenset({(names[e.source], e.source_cardinality), (names[e.target], e.target_cardinality)}) for e in parsed.edges}
        self.assertEqual(relationships, {frozenset({('Cliente', '0..1'), ('Telefono', '1..*')}),
                                         frozenset({('Cliente', '0..1'), ('Email', '1')})})

    def test_ea_primitives_use_declarations_not_id_prefix_guessing(self):
        raw = EA_FIXTURE.read_bytes()
        for name, expected in [('boolean', 'Boolean'), ('long', 'Long'), ('double', 'Double'), ('float', 'Float')]:
            with self.subTest(name=name):
                varied = raw.replace(b'name="int"', f'name="{name}"'.encode())
                parsed, _ = parse_xmi(varied)
                self.assertEqual(next(n for n in parsed.nodes if n.data.name == 'Cliente').data.attributes[0].type, expected)
        with self.assertRaisesRegex(XMIError, 'Tipo no soportado'):
            parse_xmi(raw.replace(b'xmi:id="EAJava_int"', b'xmi:id="AnotherID"'))
        with self.assertRaisesRegex(XMIError, 'Tipo no soportado'):
            parse_xmi(raw.replace(b'name="int"', b'name="UnknownType"'))

    def test_void_is_allowed_only_for_return_and_reference_whitespace_is_trimmed(self):
        raw = EA_FIXTURE.read_bytes()
        parsed, _ = parse_xmi(raw.replace(b'xmi:idref="EAJava_int"', b'xmi:idref=" EAJava_int&#x20;"'))
        self.assertEqual(next(n for n in parsed.nodes if n.data.name == 'Cliente').data.attributes[0].type, 'Integer')
        with self.assertRaisesRegex(XMIError, 'Tipo no soportado'):
            parse_xmi(raw.replace(b'xmi:idref="EAJava_int"', b'xmi:idref="EAJava_void"'))

    def test_ea_primitive_catalog_cannot_override_model_classes(self):
        raw = EA_FIXTURE.read_bytes().replace(b'xmi:id="EAJava_int"', b'xmi:id="EAID_64341587_A734_469d_A5B6_D911F3829FAD"')
        with self.assertRaisesRegex(XMIError, 'contradice el modelo'):
            parse_xmi(raw)

    def test_vendor_metadata_ids_do_not_collide_with_model_ids(self):
        baseline, _ = parse_xmi(FIXTURE.read_bytes())
        metadata = b'''<xmi:Extension extender="Enterprise Architect">
          <elements><element xmi:idref="A"><attribute xmi:id="name"/>
          <attribute xmi:id="name"/></element></elements>
          <packagedElement xmi:type="uml:Class" xmi:id="A" name="MetadataOnly"/>
        </xmi:Extension>'''
        # Both document-level and embedded extension blocks must be excluded.
        for closing in (b'</xmi:XMI>', b'</uml:Model>'):
            with self.subTest(location=closing):
                raw = FIXTURE.read_bytes().replace(closing, metadata + closing)
                parsed, warnings = parse_xmi(raw)
                self.assertEqual(parsed, baseline)
                self.assertTrue(any('extensiones' in warning for warning in warnings))

    def test_real_duplicate_definitions_still_report_locations(self):
        raw = FIXTURE.read_bytes().replace(b'xmi:id="B"', b'xmi:id="A"')
        with self.assertRaisesRegex(XMIError, r'duplicado en el modelo UML: A .*líneas'):
            parse_xmi(raw)

    def test_extension_cannot_supply_a_missing_model_definition(self):
        raw = FIXTURE.read_bytes().replace(b'type="B"', b'type="Missing"')
        raw = raw.replace(b'</xmi:XMI>', b'''<xmi:Extension extender="Enterprise Architect">
          <packagedElement xmi:type="uml:Class" xmi:id="Missing" name="MetadataOnly"/>
        </xmi:Extension></xmi:XMI>''')
        with self.assertRaisesRegex(XMIError, 'Extremo de asociación'):
            parse_xmi(raw)

    def test_empty_document_roundtrip_warns_before_replacement(self):
        parsed, warnings = parse_xmi(serialize_xmi(UMLCanvasDiagram()))
        self.assertEqual(parsed.nodes, [])
        self.assertTrue(any('vacío' in message for message in warnings))

    def test_non_string_default_expression_is_not_exported_as_a_string_literal(self):
        payload = example(); payload['nodes'][0]['data']['attributes'].append(
            {'name': 'cantidad', 'type': 'Integer', 'default_value': '42'})
        raw = serialize_xmi(UMLCanvasDiagram.model_validate(payload))
        self.assertIn(b'uml:OpaqueExpression', raw)
        parsed, _ = parse_xmi(raw)
        self.assertEqual(parsed.nodes[0].data.attributes[1].default_value, '42')

    def test_semantic_roundtrip(self):
        payload = example()
        payload['nodes'][0]['data']['attributes'][0].update(is_pk=True, is_unique=True,
            is_nullable=False, is_static=True, default_value='<value & "quoted">')
        original = UMLCanvasDiagram.model_validate(payload)
        raw = serialize_xmi(original)
        parsed, warnings = parse_xmi(raw)
        before = original.model_dump(mode='json'); after = parsed.model_dump(mode='json')
        before['metadata'] = {'viewport': None}
        before['edges'][0]['target_cardinality'] = '*'
        self.assertEqual(before, after)
        self.assertTrue(warnings)
        self.assertIn(b'&lt;value &amp;', raw)

    def test_all_relationship_types(self):
        for kind in ('association', 'aggregation', 'composition', 'generalization', 'dependency'):
            payload = example(); payload['edges'][0].update(type=kind)
            result, _ = parse_xmi(serialize_xmi(UMLCanvasDiagram.model_validate(payload)))
            edge = result.edges[0]
            with self.subTest(kind=kind):
                self.assertEqual(edge.type.value, kind)
                self.assertEqual((edge.source, edge.target), ('client', 'order'))

    def test_external_class_owned_composition_and_member_order(self):
        parsed, _ = parse_xmi(FIXTURE.read_bytes())
        names = {n.id: n.data.name for n in parsed.nodes}
        edge = parsed.edges[0]
        self.assertEqual((names[edge.source], names[edge.target]), ('Pedido', 'Linea'))
        self.assertEqual(edge.type.value, 'composition')
        self.assertEqual((edge.source_cardinality, edge.target_cardinality), ('1', '*'))
        self.assertEqual((edge.source_role, edge.target_role), ('pedido', 'lineas'))
        self.assertEqual([a.name for a in parsed.nodes[0].data.attributes], ['nombre'])

    def test_custom_types_resolve_by_id_and_package(self):
        payload = example()
        payload['nodes'][0]['data']['attributes'].append({'name': 'pedido', 'type': 'Pedido'})
        parsed, _ = parse_xmi(serialize_xmi(UMLCanvasDiagram.model_validate(payload)))
        self.assertEqual(parsed.nodes[0].data.attributes[1].type, 'com.example.model.Pedido')

    def test_security_and_malformed_inputs(self):
        samples = [b'', b'<html/>', b'<broken', b'x'*(MAX_BYTES+1),
                   b'<!DOCTYPE foo [<!ENTITY test SYSTEM "file:///secret">]><foo>&test;</foo>',
                   FIXTURE.read_bytes().replace(b'xmi:id="B"', b'xmi:id="A"'),
                   FIXTURE.read_bytes().replace(b'type="B"', b'type="missing"'),
                   FIXTURE.read_bytes().replace(b'name="Linea"', b'name="invalid name"')]
        for index, raw in enumerate(samples):
            with self.subTest(index=index), self.assertRaises(XMIError):
                parse_xmi(raw)

    def test_unsupported_models_are_reported_without_implicit_conversion(self):
        raw = FIXTURE.read_bytes().replace(b'</uml:Model>',
            b'<packagedElement xmi:type="uml:UseCase" xmi:id="I" name="Unsupported"/></uml:Model>')
        parsed, warnings = parse_xmi(raw)
        self.assertEqual(len(parsed.nodes), 2)
        self.assertTrue(any('UseCase (1)' in warning for warning in warnings))
        with self.assertRaises(XMIError):
            parse_xmi(FIXTURE.read_bytes().replace(b'#String', b'#Unknown'))

    def test_composition_export_marks_the_part_property(self):
        payload = example(); payload['edges'][0]['type'] = 'composition'
        root = etree.fromstring(serialize_xmi(UMLCanvasDiagram.model_validate(payload)))
        ends = root.xpath(".//ownedEnd[@aggregation='composite']")
        self.assertEqual(len(ends), 1)
        self.assertEqual(ends[0].get('type'), 'n_order')
        self.assertEqual(root.get(tag(XMI, 'version')), '2.5.1')


class XMIAPITests(PostgresCase):
    async def test_permissions_preview_is_read_only_and_apply_uses_version(self):
        owner, token = await self.account('owner-xmi')
        viewer, viewer_token = await self.account('viewer-xmi')
        _, outsider_token = await self.account('outsider-xmi')
        project = await self.request('POST', '/projects', 201, token, {'name': 'XMI tests'})
        path = '/projects/' + project['id']
        await self.request('PUT', path + '/members', 200, token, {'email': viewer['email'], 'role': 'VIEWER'})
        initial = await self.request('GET', path + '/canvas', 200, token)
        raw = FIXTURE.read_bytes()
        async def preview(access_token, content=raw):
            return await self.client.post('/api/v1' + path + '/xmi/preview', content=content,
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/xml'})
        self.assertEqual((await preview(viewer_token)).status_code, 403)
        self.assertEqual((await preview(outsider_token)).status_code, 404)
        response = await preview(token)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['summary']['classes'], 2)
        self.assertEqual(await self.request('GET', path + '/canvas', 200, token), initial)
        self.assertEqual((await preview(token, b'<invalid/>')).status_code, 422)
        self.assertEqual((await preview(token, b'x'*(MAX_BYTES+1))).status_code, 413)
        saved = await self.request('PUT', path + '/canvas', 200, token, data['document'])
        await self.request('PUT', path + '/canvas', 409, token, data['document'])
        export = await self.client.get('/api/v1' + path + '/xmi', headers={'Authorization': f'Bearer {viewer_token}'})
        self.assertEqual(export.status_code, 200)
        ea_export = await self.client.get('/api/v1' + path + '/xmi?format=ea15', headers={'Authorization': f'Bearer {viewer_token}'})
        self.assertEqual(ea_export.status_code, 200)
        self.assertIn('-ea15.xmi', ea_export.headers['content-disposition'])
        self.assertEqual(len(parse_xmi(ea_export.content)[0].nodes), 2)
        self.assertIn('attachment', export.headers['content-disposition'])
        self.assertEqual(len(parse_xmi(export.content)[0].nodes), 2)
        self.assertEqual(await self.request('GET', path + '/canvas', 200, token), saved)
        self.assertEqual((await self.client.get('/api/v1' + path + '/xmi')).status_code, 401)
        saved['nodes'][0]['data']['attributes'][0]['default_value'] = '\u0001'
        await self.request('PUT', path + '/canvas', 200, token, saved)
        bad_export = await self.client.get('/api/v1' + path + '/xmi', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(bad_export.status_code, 422)
