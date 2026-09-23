import unittest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.uml import UMLCanvasDiagram
from app.services.xmi.serializer import serialize_xmi
from app.services.xmi.ea_serializer import serialize_ea_xmi
from app.services.xmi.parser import parse_xmi
from app.services.generator.ast_transformer import transform, GenerationError
from db_case import PostgresCase


def visual_document():
    return UMLCanvasDiagram.model_validate({'nodes': [
        {'id': 'a', 'position': {'x': 10, 'y': 20}, 'width': 420, 'height': 240,
         'data': {'name': 'Servicio', 'kind': 'interface', 'methods': [{'name': 'crear', 'is_abstract': True}]}},
        {'id': 'b', 'position': {'x': 600, 'y': 20},
         'data': {'name': 'Estado', 'kind': 'enumeration', 'literals': ['ACTIVO', 'INACTIVO']}},
    ], 'edges': [{'id': 'e', 'source': 'a', 'target': 'b', 'source_handle': 'source-bottom', 'target_handle': 'target-top'}],
       'metadata': {'viewport': {'x': 23, 'y': 42, 'zoom': 1.3}}})


class VisualTests(unittest.TestCase):
    def test_kinds_and_literals_roundtrip_standard_and_ea(self):
        doc = visual_document()
        for raw in [serialize_xmi(doc), serialize_ea_xmi(doc, uuid4(), 'Tipos UML')]:
            restored, _ = parse_xmi(raw)
            self.assertEqual([n.data.model_dump() for n in restored.nodes], [n.data.model_dump() for n in doc.nodes])

    def test_constraints_and_legacy_defaults(self):
        old = UMLCanvasDiagram.model_validate({'nodes': [{'id': 'old', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'Inventario'}}]})
        self.assertEqual(old.nodes[0].data.kind, 'class')
        doc = visual_document().model_dump(mode='json')
        doc['nodes'][0]['width'] = -1
        with self.assertRaises(ValidationError): UMLCanvasDiagram.model_validate(doc)
        doc = visual_document().model_dump(mode='json')
        doc['nodes'][1]['data']['literals'] = ['ACTIVO', 'ACTIVO']
        with self.assertRaises(ValidationError): UMLCanvasDiagram.model_validate(doc)

    def test_spring_does_not_silently_convert_types_to_entities(self):
        with self.assertRaises(GenerationError): transform(visual_document())


class VisualPersistenceTests(PostgresCase):
    async def test_visual_fields_and_kinds_survive_database_reopen(self):
        _, token = await self.account('visual')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Visual persistence'})
        path = '/projects/' + project['id'] + '/canvas'
        payload = visual_document().model_dump(mode='json')
        saved = await self.request('PUT', path, 200, token, payload)
        reopened = await self.request('GET', path, 200, token)
        self.assertEqual(reopened, saved)
        for key in ('nodes', 'edges', 'metadata'):
            self.assertEqual(reopened[key], payload[key])
