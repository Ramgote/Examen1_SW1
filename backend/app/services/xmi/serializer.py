"""Export model semantics as UML/XMI, with a small optional canvas extension."""
from lxml import etree
from app.schemas.uml import UMLCanvasDiagram, UMLSupportedType
from app.services.xmi.common import XMI, UML, PLATFORM, VISIBILITY, child, bounds, tag, XMIError


def serialize_xmi(document: UMLCanvasDiagram) -> bytes:
    data = document.model_dump(mode='json')
    root = etree.Element(tag(XMI, 'XMI'), nsmap={'xmi': XMI, 'uml': UML, 'platform': PLATFORM})
    root.set(tag(XMI, 'version'), '2.5.1')
    child(root, tag(XMI, 'Documentation'), exporter='UMLPlatform', exporterVersion='1')
    model = child(root, tag(UML, 'Model'), id='model', name='UMLPlatformModel')
    primitives = child(model, 'packagedElement', id='primitive_types', kind='Package', name='PlatformTypes')
    for item in UMLSupportedType:
        child(primitives, 'packagedElement', id='type_' + item.value, kind='PrimitiveType', name=item.value)
    packages = {}
    classes = {}
    qualified = {f"{n['data']['package_name']}.{n['data']['name']}": 'n_' + n['id'] for n in data['nodes']}

    def type_id(name, owner):
        if name in owner['template_parameters']:
            owner_id = next(n['id'] for n in data['nodes'] if n['data'] is owner)
            return f'tt_{owner_id}_{owner["template_parameters"].index(name)}'
        if name in {t.value for t in UMLSupportedType}:
            return 'type_' + name
        if name in qualified:
            return qualified[name]
        local = owner['package_name'] + '.' + name
        if local in qualified:
            return qualified[local]
        return next(value for key, value in qualified.items() if key.rsplit('.', 1)[-1] == name)

    extension = child(root, tag(XMI, 'Extension'), extender='UMLPlatform')
    for node in data['nodes']:
        owner = node['data']; package = model; path = ''
        for part in owner['package_name'].split('.'):
            path = path + '.' + part if path else part
            if path not in packages:
                packages[path] = child(package, 'packagedElement', kind='Package', id=f'pkg_{len(packages)}', name=part)
            package = packages[path]
        cls = child(package, 'packagedElement', kind={'class': 'Class', 'interface': 'Interface', 'enumeration': 'Enumeration'}[owner['kind']], id='n_' + node['id'],
                    name=owner['name'], isAbstract=str(owner['is_abstract']).lower())
        classes[node['id']] = cls
        if owner['template_parameters']:
            signature = child(cls, 'ownedTemplateSignature', kind='RedefinableTemplateSignature', id='ts_' + node['id'])
            for index, parameter in enumerate(owner['template_parameters']):
                param = child(signature, 'ownedParameter', kind='ClassifierTemplateParameter',
                              id=f"tp_{node['id']}_{index}", parameteredElement=f"tt_{node['id']}_{index}")
                child(param, 'ownedParameteredElement', kind='Class', id=f"tt_{node['id']}_{index}", name=parameter)
        for index, literal in enumerate(owner['literals']):
            child(cls, 'ownedLiteral', kind='EnumerationLiteral', id=f"lit_{node['id']}_{index}", name=literal)
        child(extension, tag(PLATFORM, 'node'), ref='n_' + node['id'], canvasId=node['id'], **node['position'])
        for index, attr in enumerate(owner['attributes']):
            attr_id = f"a_{node['id']}_{index}"
            prop = child(cls, 'ownedAttribute', kind='Property', id=attr_id, name=attr['name'],
                         type=type_id(attr['type'], owner), visibility=VISIBILITY[attr['visibility']],
                         isStatic=str(attr['is_static']).lower(), isUnique='true', isOrdered='false')
            # UML collection uniqueness is unrelated to the database UNIQUE
            # constraint stored in our platform extension below.
            bounds(prop, '0..1' if attr['is_nullable'] else '1')
            if attr['default_value'] is not None:
                if attr['type'] in {'String', 'Text'}:
                    child(prop, 'defaultValue', kind='LiteralString', value=attr['default_value'])
                else:
                    value = child(prop, 'defaultValue', kind='OpaqueExpression')
                    child(value, 'body').text = attr['default_value']
            child(extension, tag(PLATFORM, 'attribute'), ref=attr_id,
                  isPk=str(attr['is_pk']).lower(), isUnique=str(attr['is_unique']).lower())
        for index, method in enumerate(owner['methods']):
            op = child(cls, 'ownedOperation', kind='Operation', id=f"m_{node['id']}_{index}",
                       name=method['name'], visibility=VISIBILITY[method['visibility']],
                       isAbstract=str(method['is_abstract']).lower(), isStatic=str(method['is_static']).lower())
            for param in method['parameters']:
                child(op, 'ownedParameter', kind='Parameter', name=param['name'], direction='in',
                      type=type_id(param['param_type'], owner))
            if method['return_type'] != 'void':
                child(op, 'ownedParameter', kind='Parameter', direction='return', type=type_id(method['return_type'], owner))
    for edge in data['edges']:
        eid = 'e_' + edge['id']
        if edge['type'] == 'generalization':
            child(classes[edge['source']], 'generalization', kind='Generalization', id=eid,
                  general='n_' + edge['target'])
        elif edge['type'] in {'dependency', 'realization'}:
            child(model, 'packagedElement', kind='Realization' if edge['type'] == 'realization' else 'Dependency', id=eid, name=edge['relation_name'],
                  client='n_' + edge['source'], supplier='n_' + edge['target'])
        elif edge['type'] == 'template_binding':
            target = next(n['data'] for n in data['nodes'] if n['id'] == edge['target'])
            source = next(n['data'] for n in data['nodes'] if n['id'] == edge['source'])
            parameters = target['template_parameters']
            if not parameters or set(parameters) != set(edge['template_arguments']):
                raise XMIError('Template binding: define los parámetros de plantilla en el destino y una sustitución para cada parámetro en la relación.')
            binding = child(classes[edge['source']], 'templateBinding', kind='TemplateBinding', id=eid, signature='ts_' + edge['target'])
            for index, parameter in enumerate(parameters):
                try:
                    actual = type_id(edge['template_arguments'][parameter], source)
                except StopIteration:
                    raise XMIError('Template binding: tipo de sustitución desconocido.') from None
                child(binding, 'parameterSubstitution', kind='TemplateParameterSubstitution', id=f'{eid}_sub_{index}',
                      formal=f"tp_{edge['target']}_{index}", actual=actual)
        else:
            linked = edge.get('association_node_id') if edge['type'] == 'association_class' else None
            if linked:
                assoc = classes[linked]
                eid = 'n_' + linked
                assoc.set(tag(XMI, 'type'), 'uml:AssociationClass')
                assoc.set('memberEnd', f'{eid}_target {eid}_source')
            else:
                assoc = child(model, 'packagedElement', kind='AssociationClass' if edge['type'] == 'association_class' else 'Association', id=eid,
                              name=edge['relation_name'], memberEnd=f'{eid}_target {eid}_source')
            for side in ('target', 'source'):
                end = child(assoc, 'ownedEnd', kind='Property', id=f'{eid}_{side}',
                            type='n_' + edge[side], name=edge[side + '_role'], association=eid)
                # UML aggregation belongs to the property typed by the PART.
                if side == 'target' and edge['type'] in ('composition', 'aggregation'):
                    end.set('aggregation', 'composite' if edge['type'] == 'composition' else 'shared')
                bounds(end, edge[side + '_cardinality'])
        child(extension, tag(PLATFORM, 'edge'), ref=eid, canvasId=edge['id'],
              relationName=edge['relation_name'])
    return etree.tostring(root, encoding='UTF-8', xml_declaration=True, pretty_print=True)
