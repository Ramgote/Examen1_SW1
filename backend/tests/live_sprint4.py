"""Live XMI integration plus inherited sprint-3 regression; temporary data only."""
from pathlib import Path
import unittest
import live_sprint3
from app.services.xmi.parser import parse_xmi


class LiveXMITests(live_sprint3.LiveCollaborationTests):
    async def test_ea15_preview_does_not_modify_project(self):
        _, token = await self.account('EA15 verification')
        project = await self.request('POST', '/projects', token, {'name': 'Temporary EA15 verification'}, 201)
        path = '/projects/' + project['id']
        before = await self.request('GET', path + '/canvas', token)
        raw = (Path(__file__).parent / 'fixtures' / 'ea15-tienda.xmi').read_bytes()
        preview = await self.http.post(path + '/xmi/preview', content=raw,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/xml'})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['summary'], {'classes': 4, 'relationships': 2, 'attributes': 3, 'methods': 4})
        self.assertEqual(await self.request('GET', path + '/canvas', token), before)

    async def test_xmi_preview_apply_export_and_room_notification(self):
        _, token = await self.account('XMI owner')
        editor, editor_token = await self.account('XMI editor')
        project = await self.request('POST', '/projects', token, {'name': 'Temporary XMI verification'}, 201)
        path = '/projects/' + project['id']
        await self.request('PUT', path + '/members', token, {'email': editor['email'], 'role': 'EDITOR'})
        socket = await self.socket(project['id'], editor_token)
        before = await self.snapshot(socket)
        raw = (Path(__file__).parent / 'fixtures' / 'uml-exchange.xmi').read_bytes()
        preview = await self.http.post(path + '/xmi/preview', content=raw,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/xml'})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(await self.request('GET', path + '/canvas', token), before)
        saved = await self.request('PUT', path + '/canvas', token, preview.json()['document'])
        self.assertEqual(await self.snapshot(socket, saved['version']), saved)
        await self.request('PUT', path + '/canvas', token, preview.json()['document'], 409)
        exported = await self.http.get(path + '/xmi', headers={'Authorization': f'Bearer {editor_token}'})
        self.assertEqual(exported.status_code, 200)
        parsed, _ = parse_xmi(exported.content)
        self.assertEqual({n.data.name for n in parsed.nodes}, {'Pedido', 'Linea'})
        self.assertEqual(parsed.edges[0].type.value, 'composition')
        self.assertEqual(await self.request('GET', path + '/canvas', token), saved)


if __name__ == '__main__':
    unittest.main(verbosity=2)
