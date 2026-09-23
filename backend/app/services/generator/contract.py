"""Versioned public HTTP contract derived from the persistence plan."""
import hashlib
import json


def build_contract(plan):
    entities = []
    for c in sorted(plan['classes'], key=lambda c: c['name']):
        if c['abstract']:
            continue
        attributes = [dict(name=a['name'], type=a['type'], is_pk=a['pk'],
                           is_nullable=a['nullable'], generated=a.get('generated', False),
                           unique=a['unique'], max_length=255 if a['type'] == 'String' and not a['text'] else None)
                      for a in c['all_attrs']]
        relations = [dict(name=r['name'], entity=r['other'], type=r['other_pk']['type'],
                          field=r['name'] + ('Ids' if r['many'] else 'Id'), many=r['many'],
                          writable=r['owner'], minimum=r['min'], maximum=r['max'],
                          required=bool(r['min'] or r['many']),
                          input_maximum=(r['max'] if r['max'] is not None else 1000) if r['many'] else None,
                          cascade_delete=r['composition']) for r in c['all_rels']]
        entities.append(dict(name=c['name'], tableName=c['table'], endpoint='/' + c['name'].lower(),
                             attributes=attributes, relationships=relations,
                             request_fields=[a['name'] for a in c['request_attrs']] +
                                 [r['field'] for r in relations if r['writable']] + ['entityVersion'],
                             response_fields=[a['name'] for a in attributes] +
                                 [r['field'] for r in relations] + ['entityVersion'],
                             primary_key=dict(name=c['pk']['name'], type=c['pk']['type'], generated=c['pk']['generated']),
                             operations=['list', 'get', 'create', 'update', 'delete']))
    body = dict(format_version=1, api_prefix='/api', entities=entities,
                pagination=dict(default_size=20, max_size=100, first_page=0),
                update=dict(method='PUT', version_field='entityVersion', full_replace=True))
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
    return dict(body, fingerprint=digest)
