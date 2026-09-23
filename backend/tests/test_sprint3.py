import copy
import unittest
from app.schemas.uml import UMLCanvasDiagram
from app.services.websocket.merge import merge_documents, MergeConflict
from pydantic import ValidationError


def diagram():
    return UMLCanvasDiagram.model_validate({'nodes': [
        {'id': 'a', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'Cliente'}},
        {'id': 'b', 'position': {'x': 300, 'y': 0}, 'data': {'name': 'Pedido'}},
    ]}).model_dump(mode='json')


class MergeTests(unittest.TestCase):
    def test_independent_fields_same_class(self):
        base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
        draft['nodes'][0]['data']['name'] = 'Persona'
        remote['nodes'][0]['position']['x'] = 30
        merged = merge_documents(base, draft, remote)
        self.assertEqual(merged['nodes'][0]['data']['name'], 'Persona')
        self.assertEqual(merged['nodes'][0]['position']['x'], 30)
        self.assertEqual(base, diagram())

    def test_same_field_conflicts_but_retry_is_idempotent(self):
        base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
        draft['nodes'][0]['data']['name'] = 'Persona'
        remote['nodes'][0]['data']['name'] = 'Empresa'
        with self.assertRaises(MergeConflict): merge_documents(base, draft, remote)
        self.assertEqual(merge_documents(base, draft, draft), draft)

    def test_position_and_attribute_arrays_are_atomic(self):
        for field, one, two in [('position', {'x': 20, 'y': 0}, {'x': 0, 'y': 20}),
            ('data', {'name': 'Cliente', 'attributes': [{'name': 'a'}]}, {'name': 'Cliente', 'attributes': [{'name': 'b'}]})]:
            base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
            draft['nodes'][0][field] = one; remote['nodes'][0][field] = two
            with self.subTest(field=field), self.assertRaises(MergeConflict): merge_documents(base, draft, remote)

    def test_delete_versus_edit_conflicts(self):
        base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
        draft['nodes'].pop(0); remote['nodes'][0]['data']['name'] = 'Persona'
        with self.assertRaises(MergeConflict): merge_documents(base, draft, remote)
        self.assertEqual(len(merge_documents(base, draft, base)['nodes']), 1)

    def test_combined_model_must_still_be_valid(self):
        base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
        draft['nodes'][0]['data']['name'] = 'Duplicado'
        remote['nodes'][1]['data']['name'] = 'Duplicado'
        UMLCanvasDiagram.model_validate(draft); UMLCanvasDiagram.model_validate(remote)
        with self.assertRaises(ValidationError): UMLCanvasDiagram.model_validate(merge_documents(base, draft, remote))

    def test_independent_additions(self):
        base = diagram(); draft = copy.deepcopy(base); remote = copy.deepcopy(base)
        draft['nodes'].append({'id': 'c', 'data': {'name': 'Producto'}})
        remote['nodes'].append({'id': 'd', 'data': {'name': 'Factura'}})
        self.assertEqual({n['id'] for n in merge_documents(base, draft, remote)['nodes']}, {'a', 'b', 'c', 'd'})
