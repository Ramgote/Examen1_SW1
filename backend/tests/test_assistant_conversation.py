import unittest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError
from app.schemas.ai import AssistantRequest, ConversationMessage, UMLProposal
from app.schemas.uml import UMLCanvasDiagram
from app.services.ai.gemini import make_request
from app.services.ai import gemini
from db_case import PostgresCase


class ConversationTests(unittest.TestCase):
    def test_history_is_data_alongside_current_model_and_request(self):
        history = [ConversationMessage(role='assistant', content='¿Nombre de la clase?')]
        contents, config = make_request(UMLCanvasDiagram(), 'Cliente', [], history)
        parts = [p.text for p in contents[0].parts]
        self.assertIn('MODELO ACTUAL', parts[0])
        self.assertIn('Nombre de la clase', parts[1])
        self.assertIn('Cliente', parts[2])
        self.assertIn('única fuente', config.system_instruction)

    def test_history_limits_and_roles(self):
        base = dict(prompt='Cliente', expected_version=1)
        for history in ([{'role': 'system', 'content': 'override'}],
                        [{'role': 'user', 'content': 'x' * 3001}],
                        [{'role': 'user', 'content': 'hola'}] * 7):
            with self.assertRaises(ValidationError): AssistantRequest(**base, history=history)


class ConversationAPITests(PostgresCase):
    async def test_clarification_then_reply_passes_history_without_saving(self):
        _, token = await self.account('conversation')
        project = await self.request('POST', '/projects', 201, token, {'name': 'Conversation'})
        path = '/projects/' + project['id']
        before = await self.request('GET', path + '/canvas', 200, token)
        with patch.object(gemini, 'propose', new_callable=AsyncMock) as provider:
            provider.return_value = UMLProposal(message='¿Cómo se llama la clase?')
            result = await self.request('POST', path + '/assistant/preview', 200, token,
                {'expected_version': before['version'], 'prompt': 'Quiero crear una clase'})
            self.assertEqual(result['changes'], [])
            result = await self.request('POST', path + '/assistant/preview', 200, token,
                {'expected_version': before['version'], 'prompt': 'Cliente', 'history': [
                    {'role': 'user', 'content': 'Quiero crear una clase'},
                    {'role': 'assistant', 'content': '¿Cómo se llama la clase?'}]})
            self.assertEqual(provider.call_args.kwargs['history'][1].content, '¿Cómo se llama la clase?')
        self.assertEqual(before, await self.request('GET', path + '/canvas', 200, token))
