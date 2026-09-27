"""Only whitelisted UML proposals are interpreted; never execute model functions."""
import json
from pydantic import ValidationError
from fastapi import HTTPException
from app.schemas.ai import UMLProposal
from app.schemas.uml import UMLCanvasDiagram

FUNCTION_NAME = 'propose_uml_changes'


class ProposalFormatError(HTTPException):
    """Only schema field names/error categories; never raw provider content."""
    def __init__(self, errors):
        schema = UMLProposal.model_json_schema()
        fields = set(schema.get('properties', {}))
        for definition in schema.get('$defs', {}).values():
            fields.update(definition.get('properties', {}))
        labels = {
            'missing': 'campo obligatorio ausente',
            'extra_forbidden': 'campo no permitido',
            'string_pattern_mismatch': 'nombre o multiplicidad con formato inválido',
            'enum': 'valor fuera de las opciones permitidas',
            'literal_error': 'valor fijo incorrecto',
            'string_type': 'se esperaba texto',
            'list_type': 'se esperaba una lista',
            'model_type': 'se esperaba un objeto',
            'model_attributes_type': 'se esperaba un objeto',
            'too_long': 'se supera el tamaño permitido',
            'string_too_long': 'texto demasiado largo',
            'string_too_short': 'texto vacío o demasiado corto',
            'value_error': 'no cumple las reglas UML del elemento',
        }
        self.issues = []
        for error in errors[:6]:
            path = '.'.join(str(part) if isinstance(part, int) else
                            part if part in fields else '[campo no permitido]'
                            for part in error['loc']) or 'propuesta'
            self.issues.append(f"{path}: {labels.get(error['type'], 'tipo o valor inválido')}")
        super().__init__(502, 'La respuesta de Gemini no cumple el formato UML. '
                         + '; '.join(self.issues) + '. No se modificó el diagrama.')


import re
import unicodedata

def clean_class_name(name: str) -> str:
    """Normalize class names with spaces, dots, accents to valid PascalCase identifier."""
    if not name or not isinstance(name, str):
        return "NewClass"
    nfkd = unicodedata.normalize('NFKD', str(name))
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    tokens = [t for t in re.split(r'[^A-Za-z0-9]+', ascii_name) if t]
    if not tokens:
        return "NewClass"
    cleaned = ''.join(t[0].upper() + t[1:] if len(t) > 1 else t.upper() for t in tokens)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "C" + cleaned
    return cleaned[0].upper() + cleaned[1:]


def clean_identifier(name: str, default: str = "item") -> str:
    """Normalize attribute, method, parameter, or role names with spaces, dots, parentheses to valid camelCase/snake_case."""
    if not name or not isinstance(name, str):
        return default
    # Strip parentheses and parameter signatures if embedded, e.g. "verifyPassword()" -> "verifyPassword"
    name = re.sub(r'\(.*?\)', '', str(name)).strip()
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r'[^A-Za-z0-9_]+', '_', ascii_name).strip('_')
    if not cleaned:
        return default
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


def clean_type(type_name: str, class_map: dict[str, str] = None) -> str:
    """Normalize diverse database/language data types and class types to canonical UML types."""
    if not type_name or not isinstance(type_name, str):
        return "String"
    t = str(type_name).strip()
    if class_map and t in class_map:
        return class_map[t]
    t_lower = t.lower()
    type_map = {
        'string': 'String', 'str': 'String', 'varchar': 'String', 'char': 'String', 'text': 'Text',
        'int': 'Integer', 'integer': 'Integer', 'number': 'Integer', 'smallint': 'Integer',
        'long': 'Long', 'bigint': 'Long',
        'double': 'Double', 'real': 'Double', 'numeric': 'Double',
        'float': 'Float',
        'bool': 'Boolean', 'boolean': 'Boolean',
        'bigdecimal': 'BigDecimal', 'decimal': 'BigDecimal', 'money': 'BigDecimal', 'currency': 'BigDecimal',
        'date': 'LocalDate', 'localdate': 'LocalDate',
        'datetime': 'LocalDateTime', 'localdatetime': 'LocalDateTime', 'timestamp': 'LocalDateTime', 'time': 'LocalDateTime',
        'void': 'void'
    }
    if t_lower in type_map:
        return type_map[t_lower]
    if '.' in t:
        parts = t.split('.')
        pkg = '.'.join(parts[:-1])
        cls = clean_class_name(parts[-1])
        return f"{pkg}.{cls}"
    return clean_class_name(t)


def clean_multiplicity(card: str) -> str:
    """Normalize multiplicity notation (e.g. 1,2 -> 1..2, 0..n -> 0..*, N/M -> *) to canonical UML."""
    if not card or not isinstance(card, str):
        return "1"
    c = str(card).strip().replace(' ', '')
    if ',' in c:
        parts = c.split(',')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            c = f"{parts[0]}..{parts[1]}"
        elif len(parts) == 2 and parts[0].isdigit() and parts[1] in ('*', 'n', 'N', 'm', 'M'):
            c = f"{parts[0]}..*"
    c = re.sub(r'[nNmM]', '*', c)
    if c in ('*', '1', '0..1', '0..*', '1..*'):
        return c
    if c == '*' or re.fullmatch(r'\d+', c):
        return c
    match = re.fullmatch(r'(\d+)\.\.(\*|\d+)', c)
    if match:
        lower, upper = match.groups()
        if upper == '*' or int(lower) <= int(upper):
            return c
        return f"{upper}..{lower}"
    return "1"


def clean_visibility(vis: str, default: str = "+") -> str:
    """Normalize visibility specifiers (+, -, #, ~ or words) to standard UML characters."""
    if not vis or not isinstance(vis, str):
        return default
    v = str(vis).strip().lower()
    if v in ('+', 'public'):
        return "+"
    if v in ('-', 'private'):
        return "-"
    if v in ('#', 'protected'):
        return "#"
    if v in ('~', 'package'):
        return "~"
    if '+' in str(vis):
        return "+"
    if '-' in str(vis):
        return "-"
    if '#' in str(vis):
        return "#"
    if '~' in str(vis):
        return "~"
    return default


def clean_relationship_type(rel_type: str) -> str:
    """Normalize relationship types from diverse naming conventions."""
    if not rel_type or not isinstance(rel_type, str):
        return "association"
    r = str(rel_type).strip().lower()
    if 'comp' in r:
        return "composition"
    if 'aggr' in r:
        return "aggregation"
    if 'gen' in r or 'inherit' in r or 'herencia' in r or 'extend' in r:
        return "generalization"
    if 'realiz' in r or 'implement' in r:
        return "realization"
    if 'assoc_class' in r or 'association_class' in r:
        return "association_class"
    if 'bind' in r or 'template' in r:
        return "template_binding"
    if 'dep' in r:
        return "dependency"
    return "association"


def sanitize_proposal_payload(payload: dict) -> dict:
    """Sanitize and normalize AI payload to ensure 100% adherence to UML metamodel."""
    if not isinstance(payload, dict):
        return payload

    sanitized = {
        **payload,
        'message': str(payload.get('message') or 'Propuesta generada a partir de los elementos detectados.'),
        'transcript': str(payload.get('transcript') or ''),
        'warnings': list(payload.get('warnings') or []),
        'delete_node_ids': [str(i) for i in payload.get('delete_node_ids') or [] if i],
        'delete_edge_ids': [str(i) for i in payload.get('delete_edge_ids') or [] if i],
        'upsert_nodes': [],
        'upsert_edges': [],
    }

    class_map = {}
    for node in payload.get('upsert_nodes') or []:
        if isinstance(node, dict) and isinstance(node.get('data'), dict):
            raw_name = node['data'].get('name')
            if raw_name:
                class_map[raw_name] = clean_class_name(raw_name)

    for offset, node in enumerate(payload.get('upsert_nodes') or []):
        if not isinstance(node, dict):
            continue
        data = node.get('data') or {}
        raw_name = data.get('name') or f"Class{offset+1}"
        cls_name = clean_class_name(raw_name)

        pos = node.get('position') or {}
        x = float(pos.get('x', 60 + (offset % 4) * 300))
        y = float(pos.get('y', 60 + (offset // 4) * 240))

        sanitized_attrs = []
        for a_idx, attr in enumerate(data.get('attributes') or []):
            if not isinstance(attr, dict):
                continue
            a_name = clean_identifier(attr.get('name'), default=f"attr_{a_idx+1}")
            a_type = clean_type(attr.get('type'), class_map)
            a_vis = clean_visibility(attr.get('visibility'), default="-")
            is_pk = bool(attr.get('is_pk', False) or (a_name.lower() in ('id', 'code', 'number', 'pk') and a_idx == 0))
            sanitized_attrs.append({
                'name': a_name,
                'type': a_type,
                'visibility': a_vis,
                'is_pk': is_pk,
                'is_nullable': bool(attr.get('is_nullable', not is_pk)),
                'is_unique': bool(attr.get('is_unique', False)),
                'is_static': bool(attr.get('is_static', False)),
                'default_value': str(attr['default_value']) if attr.get('default_value') is not None else None,
            })

        sanitized_methods = []
        for m_idx, method in enumerate(data.get('methods') or []):
            if not isinstance(method, dict):
                continue
            m_name = clean_identifier(method.get('name'), default=f"op_{m_idx+1}")
            m_ret = clean_type(method.get('return_type', 'void'), class_map)
            m_vis = clean_visibility(method.get('visibility'), default="+")

            sanitized_params = []
            for p_idx, p in enumerate(method.get('parameters') or []):
                if not isinstance(p, dict):
                    continue
                p_name = clean_identifier(p.get('name'), default=f"p_{p_idx+1}")
                p_type = clean_type(p.get('param_type', 'String'), class_map)
                sanitized_params.append({'name': p_name, 'param_type': p_type})

            sanitized_methods.append({
                'name': m_name,
                'return_type': m_ret,
                'visibility': m_vis,
                'parameters': sanitized_params,
                'is_static': bool(method.get('is_static', False)),
                'is_abstract': bool(method.get('is_abstract', False)),
            })

        pkg = str(data.get('package_name') or 'com.example.model')
        if not re.fullmatch(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$', pkg):
            pkg = 'com.example.model'

        sanitized['upsert_nodes'].append({
            'id': str(node.get('id') or f"node_{offset+1}"),
            'type': 'uml_class',
            'position': {'x': x, 'y': y},
            **{key: node[key] for key in ('width', 'height') if key in node},
            'data': {
                'name': cls_name,
                **{key: data[key] for key in ('kind', 'literals', 'template_parameters') if key in data},
                'is_abstract': bool(data.get('is_abstract', False)),
                'package_name': pkg,
                'attributes': sanitized_attrs,
                'methods': sanitized_methods,
            }
        })

    for e_idx, edge in enumerate(payload.get('upsert_edges') or []):
        if not isinstance(edge, dict):
            continue
        rel_type = clean_relationship_type(edge.get('type'))
        src_card = clean_multiplicity(edge.get('source_cardinality'))
        tgt_card = clean_multiplicity(edge.get('target_cardinality'))

        if rel_type == 'composition':
            src_upper = src_card.split('..')[-1]
            if src_upper == '*' or (src_upper.isdigit() and int(src_upper) > 1):
                src_card = '1'

        src_role = clean_identifier(edge.get('source_role')) if edge.get('source_role') else None
        tgt_role = clean_identifier(edge.get('target_role')) if edge.get('target_role') else None

        sanitized['upsert_edges'].append({
            'id': str(edge.get('id') or f"edge_{e_idx+1}"),
            'source': str(edge.get('source')),
            'target': str(edge.get('target')),
            'type': rel_type,
            **{key: edge[key] for key in ('source_handle', 'target_handle', 'template_arguments') if key in edge},
            'source_cardinality': src_card,
            'target_cardinality': tgt_card,
            'source_role': src_role,
            'target_role': tgt_role,
            'relation_name': str(edge['relation_name']) if edge.get('relation_name') is not None else None,
        })

    return sanitized


def parse_call(response, sanitize=False):
    candidates = response.candidates or []
    if len(candidates) != 1 or str(candidates[0].finish_reason.value if candidates[0].finish_reason else '') != 'STOP':
        raise HTTPException(502, 'Gemini no completó una propuesta. Reduce la petición o aclara su contenido.')
    parts = candidates[0].content.parts if candidates[0].content else []
    calls = [p.function_call for p in (parts or []) if p.function_call]
    if len(calls) != 1 or calls[0].name != FUNCTION_NAME:
        raise HTTPException(502, 'Gemini no devolvió la función UML esperada. Intenta reformular la petición.')
    try:
        if len(json.dumps(calls[0].args, ensure_ascii=False).encode()) > 1024 * 1024:
            raise ValueError('Proposal too large')
        args = sanitize_proposal_payload(calls[0].args) if sanitize else calls[0].args
        proposal = UMLProposal.model_validate(args)
        if any(len(w) > 1000 for w in proposal.warnings):
            raise ValueError('Warning too large')
        return proposal
    except ValidationError as exc:
        raise ProposalFormatError(exc.errors(include_input=False, include_context=False, include_url=False)) from None
    except (ValueError, TypeError):
        raise HTTPException(502, 'La respuesta de Gemini no cumple el formato UML. No se modificó el diagrama.') from None



def build_preview(original, proposal):
    before = original.model_dump(mode='json')
    nodes = {n['id']: n for n in before['nodes']}
    edges = {e['id']: e for e in before['edges']}
    def check(upserts, deleted, existing):
        ids = [item.id for item in upserts]
        if len(ids) != len(set(ids)) or len(deleted) != len(set(deleted)) or set(ids) & set(deleted):
            raise ValueError('Operaciones contradictorias o duplicadas')
        if not set(deleted) <= existing.keys():
            raise ValueError('Eliminación de identificadores inexistentes')
    try:
        check(proposal.upsert_nodes, proposal.delete_node_ids, nodes)
        check(proposal.upsert_edges, proposal.delete_edge_ids, edges)
        for key in proposal.delete_node_ids:
            del nodes[key]
        for item in proposal.upsert_nodes:
            updated = item.model_dump(mode='json')
            previous = nodes.get(item.id, {})
            for key in ('width', 'height'):
                if key not in item.model_fields_set and key in previous:
                    updated[key] = previous[key]
            for key in ('kind', 'literals', 'template_parameters'):
                if key not in item.data.model_fields_set and key in previous.get('data', {}):
                    updated['data'][key] = previous['data'][key]
            nodes[item.id] = updated
        # Deleting a class also removes all its incident edges, shown in the diff.
        edges = {k: e for k, e in edges.items() if e['source'] in nodes and e['target'] in nodes
                 and (not e.get('association_node_id') or e['association_node_id'] in nodes)
                 and k not in proposal.delete_edge_ids}
        for item in proposal.upsert_edges:
            updated = item.model_dump(mode='json')
            for key in ('source_handle', 'target_handle', 'template_arguments', 'association_node_id'):
                if key not in item.model_fields_set and key in edges.get(item.id, {}):
                    updated[key] = edges[item.id][key]
            edges[item.id] = updated
        data = {**before, 'nodes': list(nodes.values()), 'edges': list(edges.values())}
        candidate = UMLCanvasDiagram.model_validate(data)
        if len(candidate.model_dump_json().encode()) > 3 * 1024 * 1024:
            raise ValueError('El resultado supera el límite de colaboración')
    except (ValueError, ValidationError) as exc:
        # Pydantic messages exclude raw model input / attachment data.
        reason = ('; '.join(e['msg'] for e in exc.errors(include_input=False)[:4])
                  if isinstance(exc, ValidationError) else str(exc))
        raise HTTPException(422, f'Propuesta UML inválida: {reason[:1000]}. No se guardaron cambios.') from None
    changes = []
    after = candidate.model_dump(mode='json')
    for kind, field in [('class', 'nodes'), ('relationship', 'edges')]:
        old, new = ({item['id']: item for item in doc[field]} for doc in (before, after))
        for key in dict.fromkeys([*old, *new]):
            a, b = old.get(key), new.get(key)
            if a != b:
                changes.append({'kind': kind, 'id': key, 'action': 'add' if a is None else 'delete' if b is None else 'update',
                                'before': a, 'after': b})
    return {'document': candidate, 'changes': changes, 'message': proposal.message,
            'transcript': proposal.transcript, 'warnings': proposal.warnings, 'version': original.version}
