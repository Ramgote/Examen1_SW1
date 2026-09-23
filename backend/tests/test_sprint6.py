import base64
import copy
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID
from fastapi import HTTPException
from google.genai import types, errors
from pydantic import ValidationError
from sqlalchemy import update, select
from app.core.config import settings
from app.models.canvas import CanvasSnapshot
from app.models.project import ProjectCollaborator
from app.schemas.ai import AssistantRequest, Attachment, UMLProposal
from app.schemas.uml import UMLCanvasDiagram
from app.services.ai import gemini
from app.services.ai.limits import AssistantLimits, limits
from app.services.ai.tool_caller import build_preview, parse_call, FUNCTION_NAME, ProposalFormatError
from app.services.ai.vision_service import decode_attachments, MAX_BODY
from db_case import PostgresCase
from test_sprint5 import example

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


def call(args, name=FUNCTION_NAME, finish='STOP'):
    return types.GenerateContentResponse(candidates=[types.Candidate(finish_reason=finish,
        content=types.Content(parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]))])


def addition():
    return UMLProposal(message='Añadir Producto al diseño.', upsert_nodes=[{
        'id': 'producto', 'position': {'x': 800, 'y': 0}, 'data': {'name': 'Producto'}}])


class ProposalTests(unittest.TestCase):
    def test_add_update_and_delete_preserve_original_and_report_incident_edges(self):
        original = UMLCanvasDiagram.model_validate(example())
        before = original.model_dump()
        updated = original.nodes[0].model_copy(deep=True)
        updated.data.attributes[0].is_unique = False
        proposal = addition()
        proposal.upsert_nodes.append(updated)
        proposal.delete_node_ids = ['pedido']
        result = build_preview(original, proposal)
        self.assertEqual(original.model_dump(), before)
        self.assertEqual({n.id for n in result['document'].nodes}, {'cliente', 'producto'})
        self.assertEqual(result['document'].edges, [])
        self.assertEqual({(c['kind'], c['action']) for c in result['changes']},
                         {('class', 'add'), ('class', 'update'), ('class', 'delete'), ('relationship', 'delete')})
        self.assertEqual(result['version'], original.version)

    def test_invalid_proposals_cannot_be_applied(self):
        original = UMLCanvasDiagram.model_validate(example())
        proposals = [UMLProposal(message='x', delete_node_ids=['no-existe']),
                     UMLProposal(message='x', delete_node_ids=['pedido', 'pedido'])]
        duplicate = addition(); duplicate.upsert_nodes *= 2; proposals.append(duplicate)
        bad_type = addition(); bad_type.upsert_nodes[0].data.attributes = original.nodes[0].data.attributes.copy()
        bad_type = bad_type.model_dump(); bad_type['upsert_nodes'][0]['data']['attributes'][0]['type'] = 'SinDefinir'
        proposals.append(UMLProposal.model_validate(bad_type))
        bad_edge = UMLProposal(message='x', upsert_edges=[{'id': 'bad', 'source': 'cliente', 'target': 'missing'}])
        proposals.append(bad_edge)
        for proposal in proposals:
            with self.subTest(proposal=proposal.message):
                with self.assertRaises(HTTPException) as caught: build_preview(original, proposal)
                self.assertEqual(caught.exception.status_code, 422)

    def test_clarification_and_noop_have_no_changes(self):
        original = UMLCanvasDiagram.model_validate(example())
        result = build_preview(original, UMLProposal(message='¿Qué clase deseas modificar?'))
        self.assertEqual(result['changes'], [])

    def test_dc1_image_extraction_sanitization(self):
        from app.services.ai.tool_caller import sanitize_proposal_payload, UMLProposal
        raw = {
            'message': 'Diagrama DC1 digitalizado con éxito.',
            'warnings': [],
            'upsert_nodes': [
                {
                    'id': 'n_bank',
                    'data': {
                        'name': 'Bank',
                        'attributes': [{'name': 'code', 'type': 'String', 'visibility': '+'}, {'name': 'address', 'type': 'String', 'visibility': '+'}],
                        'methods': [{'name': 'manages()', 'return_type': 'void'}, {'name': 'maintains()', 'return_type': 'void'}],
                    },
                },
                {
                    'id': 'n_atm_trans',
                    'data': {
                        'name': 'ATM Transactions',
                        'attributes': [
                            {'name': 'transaction id', 'type': 'int', 'visibility': '+'},
                            {'name': 'account no.', 'type': 'varchar', 'visibility': '+'},
                            {'name': 'card number', 'type': 'text', 'visibility': '+'},
                            {'name': 'post balance', 'type': 'double', 'visibility': '+'},
                        ],
                        'methods': [{'name': '+verifyPassword()', 'return_type': 'void'}],
                    },
                },
                {
                    'id': 'n_curr_acc',
                    'data': {
                        'name': 'Current Account',
                        'attributes': [{'name': 'account no.', 'type': 'int', 'visibility': '+'}],
                        'methods': [{'name': '+withdraw()', 'return_type': 'void'}],
                    },
                },
            ],
            'upsert_edges': [
                {
                    'id': 'e1',
                    'source': 'n_bank',
                    'target': 'n_atm_trans',
                    'type': 'aggregation',
                    'source_cardinality': '1',
                    'target_cardinality': '0..n',
                },
                {
                    'id': 'e2',
                    'source': 'n_curr_acc',
                    'target': 'n_bank',
                    'type': 'generalization',
                    'source_cardinality': '1,2',
                    'target_cardinality': '1',
                },
            ],
        }
        sanitized = sanitize_proposal_payload(raw)
        validated = UMLProposal.model_validate(sanitized)
        nodes_by_id = {n.id: n.data for n in validated.upsert_nodes}
        self.assertEqual(nodes_by_id['n_atm_trans'].name, 'ATMTransactions')
        self.assertEqual(nodes_by_id['n_curr_acc'].name, 'CurrentAccount')
        attr_names = [a.name for a in nodes_by_id['n_atm_trans'].attributes]
        self.assertEqual(attr_names, ['transaction_id', 'account_no', 'card_number', 'post_balance'])
        self.assertEqual(nodes_by_id['n_atm_trans'].attributes[0].type, 'Integer')
        self.assertEqual(nodes_by_id['n_atm_trans'].attributes[1].type, 'String')
        self.assertEqual(nodes_by_id['n_atm_trans'].methods[0].name, 'verifyPassword')
        self.assertEqual(validated.upsert_edges[0].target_cardinality, '0..*')
        self.assertEqual(validated.upsert_edges[1].source_cardinality, '1..2')

    def test_tool_name_arguments_and_truncation_are_checked(self):
        self.assertEqual(parse_call(call({'message': 'Hola'})).message, 'Hola')
        for response in [call({'message': 'x'}, name='delete_database'), call({'message': 'x'}, finish='MAX_TOKENS'),
                         call({'message': 'x', 'execute': 'arbitrary code'}), types.GenerateContentResponse()]:
            with self.assertRaises(HTTPException) as caught: parse_call(response)
            self.assertEqual(caught.exception.status_code, 502)
        response = call({'message': 'x'})
        response.candidates[0].content.parts *= 2
        with self.assertRaises(HTTPException): parse_call(response)

    def test_media_validation_and_mixed_prompt(self):
        attachment = Attachment(name='diagrama.png', mime_type='image/png', data=base64.b64encode(PNG).decode())
        media = decode_attachments([attachment])
        self.assertEqual(media, [('image/png', PNG)])
        contents, config = gemini.make_request(UMLCanvasDiagram(), 'Digitaliza este boceto', media)
        self.assertEqual(contents[0].parts[-1].inline_data.data, PNG)
        self.assertEqual(config.tool_config.function_calling_config.allowed_function_names, [FUNCTION_NAME])
        self.assertTrue(config.automatic_function_calling.disable)
        declaration = config.tools[0].function_declarations[0]
        self.assertIsNone(declaration.parameters_json_schema)
        schema = declaration.parameters.model_dump(exclude_none=True)
        self.assertNotIn('$ref', str(schema))
        self.assertNotIn('$defs', str(schema))
        self.assertIn('upsert_nodes', schema['properties'])
        self.assertTrue(schema['properties']['upsert_nodes']['items']['properties']['data']['properties']['attributes']['items']['properties']['default_value']['nullable'])
        for data in ['not base64!', base64.b64encode(b'<script>bad</script>').decode(), base64.b64encode(PNG + b'x' * (4 * 1024 * 1024)).decode()]:
            with self.assertRaises(HTTPException):
                decode_attachments([attachment.model_copy(update={'data': data})])
        with self.assertRaises(ValidationError): AssistantRequest(expected_version=1)
        with self.assertRaises(ValidationError): AssistantRequest(expected_version=1, attachments=[attachment] * 4)

    def test_concurrency_and_rate_limit_release_on_error(self):
        limiter = AssistantLimits()
        with limiter.claim('user'):
            with self.assertRaises(HTTPException):
                with limiter.claim('user'): pass
        try:
            with limiter.claim('user'): raise ValueError()
        except ValueError: pass
        self.assertEqual(limiter.active, set())
        for _ in range(4):
            with limiter.claim('user'): pass
        with self.assertRaises(HTTPException):
            with limiter.claim('user'): pass


class GeminiAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_image_proposal_is_repaired_once_with_same_media_and_signature(self):
        invalid = call({'message': 'Imagen', 'upsert_nodes': [
            {'id': 'atm', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'ATM Transactions'}}]})
        invalid.candidates[0].content.role = 'model'
        invalid.candidates[0].content.parts[0].thought_signature = b'test-signature'
        corrected = call({'message': 'Nombre adaptado', 'warnings': ['ATM Transactions -> ATMTransactions'],
            'upsert_nodes': [{'id': 'atm', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'ATMTransactions'}}]})
        with patch.object(settings, 'GEMINI_API_KEY', 'test-only'), patch.object(gemini.genai, 'Client') as factory:
            client = AsyncMock()
            factory.return_value.aio.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.aio.__aexit__ = AsyncMock(return_value=False)
            client.models.generate_content.side_effect = [invalid, corrected]
            original = UMLCanvasDiagram.model_validate(example())
            before = original.model_dump()
            result = await gemini.propose(original, 'Digitaliza', [('image/png', PNG)])
            self.assertEqual(result.upsert_nodes[0].data.name, 'ATMTransactions')
            self.assertEqual(client.models.generate_content.await_count, 2)
            sent = client.models.generate_content.call_args.kwargs['contents']
            self.assertEqual(sent[0].parts[-1].inline_data.data, PNG)
            self.assertEqual(sent[1].parts[0].thought_signature, b'test-signature')
            self.assertIn('upsert_nodes.0.data.name', str(sent[2].parts[0].function_response.response))
            preview = build_preview(original, result)
            self.assertEqual(len(preview['document'].nodes), len(original.nodes) + 1)
            self.assertEqual(original.model_dump(), before)

    async def test_second_invalid_response_stops_and_reports_safe_fields(self):
        response = call({'message': 'Imagen', 'upsert_nodes': [
            {'id': 'atm', 'position': {'x': 0, 'y': 0}, 'data': {'name': 'ATM Transactions'}}],
            'private-unknown-field': 'private-value'})
        with patch.object(settings, 'GEMINI_API_KEY', 'test-only'), patch.object(gemini.genai, 'Client') as factory:
            client = AsyncMock()
            factory.return_value.aio.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.aio.__aexit__ = AsyncMock(return_value=False)
            client.models.generate_content.return_value = response
            with self.assertRaises(ProposalFormatError) as caught:
                await gemini.propose(UMLCanvasDiagram(), 'Imagen', [('image/png', PNG)])
            self.assertEqual(client.models.generate_content.await_count, 2)
            self.assertIn('upsert_nodes.0.data.name', caught.exception.detail)
            self.assertNotIn('private-', caught.exception.detail)
            self.assertNotIn('ATM Transactions', caught.exception.detail)

    def test_constraints_are_transmitted_in_function_schema(self):
        schema = gemini.function_schema()
        node = schema.properties['upsert_nodes'].items
        self.assertIn('pattern=', node.properties['data'].properties['name'].description)
        edge = schema.properties['upsert_edges'].items
        self.assertIn('pattern=', edge.properties['source_cardinality'].description)

    async def test_missing_key_is_explicit_and_no_client_created(self):
        with patch.object(settings, 'GEMINI_API_KEY', ''), patch.object(gemini.genai, 'Client') as client:
            with self.assertRaises(HTTPException) as caught: await gemini.propose(UMLCanvasDiagram(), 'Hola', [])
            self.assertEqual(caught.exception.status_code, 503)
            client.assert_not_called()

    async def test_sdk_payload_response_and_sanitized_errors(self):
        with patch.object(settings, 'GEMINI_API_KEY', 'test-only'), patch.object(gemini.genai, 'Client') as factory:
            client = AsyncMock()
            factory.return_value.aio.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.aio.__aexit__ = AsyncMock(return_value=False)
            client.models.generate_content.return_value = call({'message': 'Propuesta', 'transcript': 'crear clase'})
            result = await gemini.propose(UMLCanvasDiagram(), 'Hola', [('image/png', PNG)])
            self.assertEqual(result.transcript, 'crear clase')
            sent = client.models.generate_content.call_args.kwargs
            self.assertEqual(sent['model'], settings.GEMINI_MODEL)
            self.assertEqual(sent['contents'][0].parts[-1].inline_data.data, PNG)
            for exc, status in [(TimeoutError('secret'), 504), (RuntimeError('secret'), 502),
                                (errors.ClientError(429, {'error': {'message': 'secret'}}), 429),
                                (errors.ClientError(404, {'error': {'message': 'secret'}}), 503),
                                (errors.ServerError(503, {'error': {'message': 'secret'}}), 503),
                                (errors.ClientError(403, {'error': {'message': 'secret'}}), 503)]:
                client.models.generate_content.side_effect = exc
                with self.assertRaises(HTTPException) as caught: await gemini.propose(UMLCanvasDiagram(), 'Hola', [])
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn('secret', caught.exception.detail)


class AssistantAPITests(PostgresCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        limits.requests.clear()
        owner, self.token = await self.account('owner')
        editor, self.editor_token = await self.account('editor')
        viewer, self.viewer_token = await self.account('viewer')
        _, self.outsider_token = await self.account('outsider')
        self.editor_id = UUID(editor['id'])
        project = await self.request('POST', '/projects', 201, self.token, {'name': 'AI tests'})
        self.project_id = UUID(project['id'])
        self.path = '/projects/' + project['id']
        await self.request('PUT', self.path + '/members', 200, self.token, {'email': editor['email'], 'role': 'EDITOR'})
        await self.request('PUT', self.path + '/members', 200, self.token, {'email': viewer['email'], 'role': 'VIEWER'})
        self.saved = await self.request('PUT', self.path + '/canvas', 200, self.token, dict(example(), version=1))
        self.payload = {'prompt': 'Añade Producto', 'expected_version': self.saved['version']}

    async def test_permissions_status_and_preview_do_not_write(self):
        route = self.path + '/assistant/preview'
        with patch.object(settings, 'GEMINI_API_KEY', ''), patch.object(gemini, 'propose', new_callable=AsyncMock) as provider:
            provider.return_value = addition()
            await self.request('POST', route, 401, body=self.payload)
            await self.request('POST', route, 404, self.outsider_token, self.payload)
            await self.request('POST', route, 403, self.viewer_token, self.payload)
            provider.assert_not_called()
            status = await self.request('GET', self.path + '/assistant/status', 200, self.token)
            self.assertFalse(status['configured'])
            self.assertNotIn('api_key', str(status).lower())
            proposal = await self.request('POST', route, 200, self.editor_token, self.payload)
            self.assertEqual(len(proposal['changes']), 1)
            self.assertEqual(await self.request('GET', self.path + '/canvas', 200, self.token), self.saved)
            applied = await self.request('PUT', self.path + '/canvas', 200, self.editor_token, proposal['document'])
            self.assertEqual(applied['version'], self.saved['version'] + 1)
            await self.request('PUT', self.path + '/canvas', 409, self.editor_token, proposal['document'])

    async def test_stale_invalid_oversize_and_unconfigured_requests(self):
        route = self.path + '/assistant/preview'
        with patch.object(gemini, 'propose', new_callable=AsyncMock) as provider:
            await self.request('POST', route, 409, self.token, {**self.payload, 'expected_version': 1})
            await self.request('POST', route, 422, self.token, {'expected_version': self.saved['version']})
            await self.request('POST', route, 422, self.token, {**self.payload, 'attachments': [{'name': 'x.png', 'mime_type': 'image/png', 'data': '!!!'}]})
            response = await self.client.post('/api/v1' + route, content=b'x' * (MAX_BODY + 1),
                headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 413)
            provider.assert_not_called()
        with patch.object(settings, 'GEMINI_API_KEY', ''):
            await self.request('POST', route, 503, self.token, self.payload)

    async def test_image_and_voice_share_the_same_request(self):
        import io, wave
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000); audio.writeframes(b'\x00' * 3200)
        attachments = [{'name': 'sketch.png', 'mime_type': 'image/png', 'data': base64.b64encode(PNG).decode()},
                       {'name': 'voice.wav', 'mime_type': 'audio/wav', 'data': base64.b64encode(output.getvalue()).decode()}]
        with patch.object(gemini, 'propose', new_callable=AsyncMock) as provider:
            proposal = addition(); proposal.transcript = 'Añadir Producto'
            provider.return_value = proposal
            result = await self.request('POST', self.path + '/assistant/preview', 200, self.token, {**self.payload, 'attachments': attachments})
            self.assertEqual([mime for mime, _ in provider.call_args.args[2]], ['image/png', 'audio/wav'])
            self.assertEqual(result['transcript'], proposal.transcript)

    async def test_concurrent_edit_or_revocation_rejected_after_provider_returns(self):
        async def concurrent_edit(*args):
            await self.db.execute(update(CanvasSnapshot).where(CanvasSnapshot.project_id == self.project_id)
                                  .values(version=CanvasSnapshot.version + 1))
            return addition()
        with patch.object(gemini, 'propose', side_effect=concurrent_edit):
            await self.request('POST', self.path + '/assistant/preview', 409, self.token, self.payload)
        self.payload['expected_version'] += 1
        async def revoke(*args):
            await self.db.execute(update(ProjectCollaborator).where(ProjectCollaborator.project_id == self.project_id,
                ProjectCollaborator.user_id == self.editor_id).values(role='VIEWER'))
            return addition()
        with patch.object(gemini, 'propose', side_effect=revoke):
            await self.request('POST', self.path + '/assistant/preview', 403, self.editor_token, self.payload)

