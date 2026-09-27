"""Ephemeral leases. All access is serialized by ConnectionManager.lock(project)."""
from time import monotonic
from fastapi import HTTPException

LEASE_SECONDS = 45


def affected_classes(before, after):
    affected = set()
    for field in ('nodes', 'edges'):
        old = {item['id']: item for item in before[field]}
        new = {item['id']: item for item in after[field]}
        for key in old.keys() | new.keys():
            if old.get(key) == new.get(key):
                continue
            if field == 'nodes':
                affected.add(key)
            else:
                for item in (old.get(key), new.get(key)):
                    if item:
                        affected.update((item['source'], item['target']))
                        if item.get('association_node_id'):
                            affected.add(item['association_node_id'])
    return affected


class Reservations:
    def __init__(self):
        self.items = {}

    def prune(self, project):
        now = monotonic()
        for key, lease in list(self.items.items()):
            if key[0] == project and lease['expires'] <= now:
                del self.items[key]

    def check(self, project, ids, owner=None):
        self.prune(project)
        for node_id in ids:
            lease = self.items.get((project, node_id))
            if lease and lease['connection_id'] != owner:
                raise HTTPException(423, f"Clase reservada por {lease['name']}. Espera a que termine su edición.")

    def acquire(self, project, ids, peer):
        self.check(project, ids, peer.id)
        existing = {key[1] for key in self.items if key[0] == project}
        if len(existing | set(ids)) > 400:
            raise HTTPException(423, 'La sala alcanzó el límite de reservas.')
        for node_id in ids:
            self.items[project, node_id] = dict(node_id=node_id, connection_id=peer.id,
                name=peer.name, expires=monotonic() + LEASE_SECONDS)

    def renew(self, project, owner):
        self.prune(project)
        for (pid, _), lease in self.items.items():
            if pid == project and lease['connection_id'] == owner:
                lease['expires'] = monotonic() + LEASE_SECONDS

    def release(self, project, owner):
        for key, lease in list(self.items.items()):
            if key[0] == project and lease['connection_id'] == owner:
                del self.items[key]

    def public(self, project):
        self.prune(project)
        return [{k: v for k, v in lease.items() if k != 'expires'}
                for (pid, _), lease in self.items.items() if pid == project]
