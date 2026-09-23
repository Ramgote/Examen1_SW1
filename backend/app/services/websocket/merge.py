"""Three-way merge. Lists without stable element IDs are deliberately atomic."""
from copy import deepcopy


class MergeConflict(ValueError):
    pass


MISSING = object()


def merge_value(base, draft, current, path=''):
    if draft == base:
        return current
    if current == base or current == draft:
        return draft
    if all(isinstance(value, dict) for value in (base, draft, current)) and not path.endswith('/position'):
        result = {}
        for key in dict.fromkeys([*current, *draft, *base]):
            value = merge_value(base.get(key, MISSING), draft.get(key, MISSING),
                                current.get(key, MISSING), f'{path}/{key}')
            if value is not MISSING:
                result[key] = value
        return result
    raise MergeConflict(f'Ediciones incompatibles en {path}. Descarga tu borrador antes de recargar.')


def merge_documents(base, draft, current):
    result = deepcopy(current)
    for field in ('nodes', 'edges'):
        maps = [{item['id']: item for item in doc[field]} for doc in (base, draft, current)]
        result[field] = list(merge_value(*maps, path=field).values())
    result['metadata'] = deepcopy(merge_value(base['metadata'], draft['metadata'], current['metadata'], 'metadata/position'))
    return result
