import copy
import json
import unittest
from app.schemas.uml import UMLCanvasDiagram
from app.services.generator.spring_boot.renderer import render
from app.services.generator.ast_transformer import GenerationError
from test_sprint5 import example


class ContractTests(unittest.TestCase):
    def test_metadata_controller_cannot_be_overwritten_by_entity(self):
        data = example()
        data['nodes'][0]['data']['name'] = 'Contract'
        with self.assertRaises(GenerationError):
            self.contract(data)

    def contract(self, data):
        files, _ = render(UMLCanvasDiagram.model_validate(data))
        self.assertEqual(files['mobile-contract.json'], files['src/main/resources/mobile-contract.json'])
        self.assertIn('/api/_meta/contract', files['src/main/java/com/generated/api/ContractController.java'])
        return json.loads(files['mobile-contract.json'])

    def test_contract_matches_request_relationships_and_pk(self):
        c = self.contract(example())
        entities = {e['name']: e for e in c['entities']}
        self.assertEqual(entities['Pedido']['endpoint'], '/pedido')
        self.assertIn('clienteId', entities['Pedido']['request_fields'])
        self.assertNotIn('id', entities['Pedido']['request_fields'])
        self.assertTrue(entities['Cliente']['primary_key']['generated'])
        self.assertFalse(entities['Cliente']['relationships'][0]['writable'])

    def test_visual_changes_do_not_change_contract_but_fields_do(self):
        data = example()
        baseline = self.contract(data)['fingerprint']
        data['version'] = 25
        data['nodes'][0]['position']['x'] = 999
        self.assertEqual(self.contract(data)['fingerprint'], baseline)
        data['nodes'][0]['data']['attributes'][0]['name'] = 'apellido'
        self.assertNotEqual(self.contract(data)['fingerprint'], baseline)

    def test_inherited_fields_and_assigned_key(self):
        data = copy.deepcopy(example())
        data['edges'] = [dict(id='g', source='pedido', target='cliente', type='generalization')]
        data['nodes'][0]['data']['is_abstract'] = True
        data['nodes'][0]['data']['attributes'].append(dict(name='codigo', type='String', is_pk=True))
        entities = self.contract(data)['entities']
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['primary_key'], dict(name='codigo', type='String', generated=False))
        self.assertIn('nombre', entities[0]['request_fields'])
