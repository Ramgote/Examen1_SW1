"""HTTP smoke test against the synthetic project from prepare_sprint5.py only."""
import os
import time
from uuid import uuid4
import httpx

base = os.environ['GENERATED_API_BASE_URL']
with httpx.Client(base_url=base, timeout=10) as client:
    for attempt in range(60):
        try:
            response = client.get('/api/cliente')
            if response.status_code == 200:
                break
        except httpx.TransportError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('El JAR no respondió dentro del plazo')
    owner_id = None
    try:
        response = client.post('/api/cliente', json={'nombre': 'http-sprint5-' + uuid4().hex})
        assert response.status_code == 201, response.text
        owner_id = response.json()['id']
        response = client.post('/api/pedido', json={'total': 12.5, 'clienteId': owner_id})
        assert response.status_code == 201, response.text
        order = response.json()
        related = client.get(f'/api/cliente/{owner_id}/pedidos')
        assert related.status_code == 200 and order['id'] in related.json(), related.text
        response = client.put(f"/api/pedido/{order['id']}", json={
            'total': 25, 'clienteId': owner_id, 'entityVersion': order['entityVersion']})
        assert response.status_code == 200 and response.json()['total'] == 25, response.text
        response = client.delete(f'/api/cliente/{owner_id}')
        assert response.status_code == 204, response.text
        owner_id = None
        assert client.get(f"/api/pedido/{order['id']}").status_code == 404
        print('HTTP real OK: crear Cliente/Pedido, consultar relación, actualizar y eliminar en cascada.')
    finally:
        if owner_id is not None:
            client.delete(f'/api/cliente/{owner_id}')
