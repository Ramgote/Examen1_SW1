"""UML -> explicit, validated persistence plan. Never execute model text."""
import hashlib
import re
from app.schemas.uml import UMLCanvasDiagram

JAVA_TYPES = {'String': 'String', 'Text': 'String', 'Integer': 'Integer', 'Long': 'Long',
              'Double': 'Double', 'Float': 'Float', 'Boolean': 'Boolean',
              'BigDecimal': 'BigDecimal', 'LocalDate': 'LocalDate', 'LocalDateTime': 'LocalDateTime'}
RESERVED = set(('abstract assert boolean break byte case catch char class const continue default do double else enum '
                'extends final finally float for goto if implements import instanceof int interface long native new '
                'package private protected public return short static strictfp super switch synchronized this throw throws '
                'transient try void volatile while true false null record sealed permits yield var _').split())
CLASS_RESERVED = set(JAVA_TYPES.values()) | {'Contract', 'Application', 'Entity', 'Table', 'Id', 'Column', 'Version', 'List', 'Set',
    'Map', 'Object', 'System', 'Math', 'Override', 'Optional', 'Collection', 'Collections', 'HashSet', 'LinkedHashSet',
    'GeneratedValue', 'GenerationType', 'Inheritance', 'InheritanceType', 'FetchType', 'CascadeType', 'JoinColumn',
    'JoinTable', 'OneToOne', 'OneToMany', 'ManyToOne', 'ManyToMany', 'Size', 'NotNull', 'EntityManager', 'Request',
    'Response', 'Service', 'Page', 'PageRequest', 'Sort', 'Objects', 'Transactional', 'ResponseStatusException'}


class GenerationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(errors))


def cap(name):
    return name[0].upper() + name[1:]


def sql_name(prefix, name):
    return prefix + re.sub(r'([A-Z])', r'_\1', name).lower()[:35] + '_' + hashlib.sha256(name.encode()).hexdigest()[:8]


def bounds(card):
    if card == '*':
        return 0, None
    parts = card.split('..')
    return int(parts[0]), None if parts[-1] == '*' else int(parts[-1])


def transform(diagram: UMLCanvasDiagram):
    errors, warnings = [], []
    if any(n.data.template_parameters for n in diagram.nodes):
        raise GenerationError(['El perfil Spring CRUD no genera clases plantilla. Conserva los parámetros en UML/XMI o utiliza un modelo de clases concretas para generar.'])
    classes = {}
    if not diagram.nodes:
        errors.append('Añade al menos una clase al diagrama.')
    unsupported = [n.data.name for n in diagram.nodes if n.data.kind != 'class']
    if unsupported:
        raise GenerationError(['El perfil CRUD Spring solo admite clases persistentes; interfaces y enumeraciones requieren un perfil de generación adicional: ' + ', '.join(unsupported)])
    names = [n.data.name for n in diagram.nodes]
    if len(names) != len({name.lower() for name in names}):
        errors.append('Este perfil requiere nombres de clase únicos entre paquetes.')
    for node in diagram.nodes:
        data = node.data
        if data.name in CLASS_RESERVED or data.name.endswith(('Repository', 'Service', 'Controller', 'Request', 'Response')):
            errors.append(f'{data.name}: nombre reservado por el generador Java.')
        attrs = []
        for a in data.attributes:
            if not re.fullmatch('[a-z][A-Za-z0-9]*', a.name) or a.name in RESERVED or a.name in {'entityVersion', 'class'}:
                errors.append(f'{data.name}.{a.name}: usa un nombre camelCase válido y no reservado en Java.')
            if a.type not in JAVA_TYPES:
                errors.append(f'{data.name}.{a.name}: representa las referencias a clases mediante una relación UML.')
            if a.is_static or a.default_value is not None:
                errors.append(f'{data.name}.{a.name}: este perfil no transforma atributos estáticos ni valores predeterminados; retíralos antes de generar.')
            attrs.append({'name': a.name, 'cap': cap(a.name), 'type': JAVA_TYPES.get(a.type, 'String'),
                          'pk': a.is_pk, 'nullable': a.is_nullable and not a.is_pk, 'unique': a.is_unique,
                          'text': a.type == 'Text', 'column': sql_name('f_', a.name)})
        if data.methods:
            warnings.append(f'{data.name}: los métodos UML se conservan en model.json; su lógica de negocio no se infiere. Se generan servicios CRUD.')
        classes[node.id] = {'id': node.id, 'name': data.name, 'abstract': data.is_abstract,
                            'table': sql_name('t_', data.name), 'attrs': attrs, 'rels': [], 'parent': None}
    for e in diagram.edges:
        if e.type == 'generalization':
            c = classes[e.source]
            if c['parent']:
                errors.append(f"{c['name']}: Java no admite herencia múltiple de clases.")
            c['parent'] = classes[e.target]
        elif e.type in {'dependency', 'realization', 'template_binding'}:
            warnings.append(f'Relación {e.id}: {e.type} se conserva en model.json; no crea una clave foránea.')
    def inherit(c):
        if 'all_attrs' in c:
            return
        p = c['parent']
        if p:
            inherit(p)
            if any(a['pk'] for a in c['attrs']):
                errors.append(f"{c['name']}: la subclase hereda la clave primaria; elimina su PK propia.")
            if {a['name'] for a in c['attrs']} & {a['name'] for a in p['all_attrs']}:
                errors.append(f"{c['name']}: un atributo oculta otro heredado.")
            c['pk'] = p['pk']
            c['all_attrs'] = p['all_attrs'] + c['attrs']
        else:
            keys = [a for a in c['attrs'] if a['pk']]
            if len(keys) > 1:
                errors.append(f"{c['name']}: las claves compuestas no están soportadas en este perfil.")
            if not keys:
                if any(a['name'] == 'id' for a in c['attrs']):
                    errors.append(f"{c['name']}: marca el atributo id como PK o cambia su nombre.")
                key = {'name': 'id', 'cap': 'Id', 'type': 'Long', 'pk': True, 'nullable': False,
                       'unique': False, 'text': False, 'column': 'id', 'generated': True}
                c['attrs'].insert(0, key)
                warnings.append(f"{c['name']}: sin PK explícita; se genera id Long autoincremental sin modificar el lienzo.")
            else:
                key = keys[0]
                if key['type'] not in {'Long', 'Integer', 'String'} or key['text']:
                    errors.append(f"{c['name']}: la PK debe ser Long, Integer o String (no Text).")
                key['generated'] = False
            c['pk'] = key
            c['all_attrs'] = c['attrs'][:]
        c['root'] = p['root'] if p else c['name']
    for c in classes.values():
        inherit(c)
    composition_parts = set()
    for e in diagram.edges:
        if e.type in {'generalization', 'dependency', 'realization', 'template_binding'}:
            continue
        source, target = classes[e.source], classes[e.target]
        slo, shi = bounds(e.source_cardinality)
        tlo, thi = bounds(e.target_cardinality)
        if shi == 0 or thi == 0:
            errors.append(f'Relación {e.id}: una multiplicidad máxima cero no puede persistirse como relación.')
        sm, tm = shi is None or shi > 1, thi is None or thi > 1
        # The many-to-one end owns the FK. For 1:1 and N:M, source owns it.
        source_owns = not (not sm and tm)
        pair = []
        suffix = hashlib.sha256(e.id.encode()).hexdigest()[:8]
        for c, other, role, lo, hi, many, own in (
            (source, target, e.target_role, tlo, thi, tm, source_owns),
            (target, source, e.source_role, slo, shi, sm, not source_owns)):
            name = role or other['name'][0].lower() + other['name'][1:] + 'Rel' + suffix
            if not re.fullmatch('[a-z][A-Za-z0-9]*', name) or name in RESERVED or name in {'entityVersion', 'list', 'get', 'create', 'update', 'delete', 'require', 'apply'}:
                errors.append(f'Relación {e.id}: rol {name} no válido en Java; usa camelCase.')
            rel = {'name': name, 'cap': cap(name), 'other': other['name'], 'other_pk': other['pk'],
                   'many': many, 'owner': own, 'min': lo, 'max': hi, 'composition': e.type == 'composition' and c is source,
                   'join': 'r_' + suffix, 'column': 'fk_' + suffix, 'edge': e.id}
            if lo > 1000 or (hi is not None and hi > 1000):
                errors.append(f'Relación {e.id}: este perfil admite límites numéricos hasta 1000; usa * para un máximo abierto.')
            pair.append(rel)
            c['rels'].append(rel)
        a, b = pair
        a['inverse'], b['inverse'] = b['name'], a['name']
        a['kind'] = 'ManyToMany' if sm and tm else 'OneToMany' if tm else 'ManyToOne' if sm else 'OneToOne'
        b['kind'] = 'ManyToMany' if sm and tm else 'ManyToOne' if tm else 'OneToMany' if sm else 'OneToOne'
        if e.type == 'composition':
            if source is target or target['id'] in composition_parts or source['parent'] or target['parent']:
                errors.append(f'Relación {e.id}: composición recursiva, con varias propiedades de dueño o con herencia no soportada.')
            composition_parts.add(target['id'])
        for rel in pair:
            if not rel['owner'] and (rel['min'] > 0 or rel['max'] not in (None, 1)):
                warnings.append(f"{rel['edge']} / {rel['name']}: el mínimo/máximo del extremo inverso requiere validación del agregado; JPA no garantiza esa regla global.")
    def relations(c):
        if 'all_rels' in c:
            return
        if c['parent']:
            relations(c['parent'])
        c['all_rels'] = (c['parent']['all_rels'] if c['parent'] else []) + c['rels']
        fields = [a['name'] for a in c['all_attrs']] + [r['name'] for r in c['all_rels']]
        dto_fields = [a['name'] for a in c['all_attrs']] + [r['name'] + ('Ids' if r['many'] else 'Id') for r in c['all_rels']]
        if len(fields) != len(set(fields)) or len(dto_fields) != len(set(dto_fields)):
            errors.append(f"{c['name']}: roles, atributos o campos de identificadores generan nombres duplicados.")
        c['request_attrs'] = [a for a in c['all_attrs'] if not a.get('generated')]
        c['owned_rels'] = [r for r in c['all_rels'] if r['owner']]
    for c in classes.values():
        relations(c)
    # Prevent recursive remove cascades across longer composition cycles.
    graph = {k: [] for k in classes}
    for e in diagram.edges:
        if e.type == 'composition':
            graph[e.source].append(e.target)
    visited, visiting = set(), set()
    def cycle(k):
        if k in visiting:
            return True
        if k in visited:
            return False
        visiting.add(k)
        if any(cycle(n) for n in graph[k]):
            return True
        visiting.remove(k)
        visited.add(k)
        return False
    if any(cycle(k) for k in graph):
        errors.append('La composición contiene un ciclo de eliminación en cascada.')
    if errors:
        raise GenerationError(errors)
    return {'classes': list(classes.values()), 'warnings': warnings, 'version': diagram.version}
