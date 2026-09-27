"""Bounded, offline-only parser for the supported UML 2.x class profile."""
import hashlib
import math
from collections import Counter
from lxml import etree
from pydantic import ValidationError
from app.schemas.uml import UMLCanvasDiagram, UMLSupportedType
from app.services.xmi.common import XMI, UML, PLATFORM, VISIBILITY, MAX_BYTES, XMIError, tag

XMI_NAMESPACES = {XMI, 'http://schema.omg.org/spec/XMI/2.1', 'http://www.omg.org/XMI',
                  'http://www.omg.org/spec/XMI/20110701'}
UML_NAMESPACES = {UML, 'http://www.omg.org/spec/UML/20161101',
                  'http://www.omg.org/spec/UML/20110701', 'http://schema.omg.org/spec/UML/2.1',
                  'http://schema.omg.org/spec/UML/2.0', 'http://www.eclipse.org/uml2/5.0.0/UML'}
ALIASES = {'int': 'Integer', 'integer': 'Integer', 'string': 'String', 'boolean': 'Boolean',
           'bool': 'Boolean', 'long': 'Long', 'double': 'Double', 'float': 'Float', 'Real': 'Double'}


def local(element):
    return etree.QName(element).localname


def xattr(element, name):
    return next((element.get(tag(ns, name)) for ns in XMI_NAMESPACES if element.get(tag(ns, name)) is not None), None)


def kind(element):
    value = xattr(element, 'type')
    return value.split(':')[-1] if value else local(element)


def children(element, name):
    return [c for c in element if local(c) == name]


def type_reference(element):
    ref = element.get('type')
    nested = children(element, 'type')
    if not ref and nested:
        ref = xattr(nested[0], 'idref')
    return ref.strip() if ref else None


def reference(element, field):
    nested = children(element, field)
    return element.get(field) or (xattr(nested[0], 'idref') if len(nested) == 1 else None)


def is_extension(element):
    return local(element) == 'Extension' and etree.QName(element).namespace in XMI_NAMESPACES | {None}


def semantic_elements(element):
    """Vendor extensions have their own metadata; never treat it as UML definitions."""
    if is_extension(element):
        return
    yield element
    for item in element:
        yield from semantic_elements(item)


def boolean(value, default=False):
    if value is None:
        return default
    if value not in ('true', 'false', '1', '0'):
        raise XMIError(f'Booleano XMI inválido: {value[:60]}')
    return value in ('true', '1')


def multiplicity(element):
    def value(name):
        items = children(element, name)
        return items[0].get('value', '0') if items else '1'
    lower, upper = value('lowerValue'), value('upperValue')
    # EA 17 can encode the shorthand '*' as two unlimited bounds.
    # Normalize only that pair; other negative bounds remain invalid.
    if lower in ('-1', '*') and upper in ('-1', '*'):
        return '*'
    if upper == '-1':
        upper = '*'
    return lower if lower == upper else ('*' if (lower, upper) == ('0', '*') else f'{lower}..{upper}')


def parse_xmi(raw: bytes):
    if not raw or len(raw) > MAX_BYTES:
        raise XMIError('El archivo debe contener XML y no superar 4 MiB')
    try:
        root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, load_dtd=False,
            no_network=True, huge_tree=False, remove_comments=True, remove_pis=True))
    except etree.XMLSyntaxError:
        raise XMIError('XML mal formado o con profundidad excesiva') from None
    if root.getroottree().docinfo.doctype:
        raise XMIError('No se permiten DTD ni entidades XML')
    if not ((local(root) == 'XMI' and etree.QName(root).namespace in XMI_NAMESPACES)
            or (local(root) == 'Model' and etree.QName(root).namespace in UML_NAMESPACES)):
        raise XMIError('Se requiere XMI 2.x con modelo UML. En EA 17.0 exporta UML 2.1 / XMI 2.1 incluyendo diagramas; XMI 1.x y Native XML/XEA no están soportados')
    if xattr(root, 'version') and not xattr(root, 'version').startswith('2.'):
        raise XMIError('Solo se admite intercambio XMI 2.x')
    elements = list(root.iter())
    if len(elements) > 50000:
        raise XMIError('El documento supera 50.000 elementos XML')
    index = {}
    for element in semantic_elements(root):
        identifier = xattr(element, 'id')
        if identifier:
            if identifier in index:
                first = index[identifier]
                raise XMIError(f'Identificador XMI duplicado en el modelo UML: {identifier[:100]} '
                               f'(líneas {first.sourceline} y {element.sourceline})')
            index[identifier] = element
    models = [root] if local(root) == 'Model' else [c for c in root if local(c) == 'Model']
    if len(models) != 1:
        raise XMIError('Se requiere exactamente un modelo UML en el archivo')
    model = models[0]
    warnings = []
    extension = {}
    container_ids = set()
    doc_elements = {}
    for el in root.iter():
        i = xattr(el, 'id')
        if i: doc_elements[i] = el
        ir = xattr(el, 'idref') or el.get('idref')
        if ir: doc_elements[ir] = el
    ea_primitives = {}
    ea_attribute_types = {}
    ea_positions = {}
    for ext in (e for e in elements if is_extension(e)
                and not any(is_extension(parent) for parent in e.iterancestors())):
        if ext.get('extender') == 'UMLPlatform':
            for item in ext:
                if etree.QName(item).namespace == PLATFORM:
                    key = (local(item), item.get('ref'))
                    if key in extension:
                        raise XMIError('Metadatos de extensión duplicados')
                    extension[key] = item
                    if local(item) == 'container' and item.get('ref'):
                        container_ids.add(item.get('ref'))
        else:
            warnings.append('Las extensiones de otras herramientas solo se interpretan para los datos expresamente soportados; no se garantiza fidelidad visual completa.')
            # EA 15 puts actual language type declarations here, unlike its
            # repeated element/connector metadata. Read only this typed catalog.
            if ext.get('extender') == 'Enterprise Architect':
                diagrams = [d for group in children(ext, 'diagrams') for d in children(group, 'diagram')
                            if any(p.get('type') in {'Logical', 'Class'} for p in children(d, 'properties'))]
                if diagrams:
                    if len(diagrams) > 1:
                        warnings.append('Hay varios diagramas de clases: se usa la distribución del primero; se importan las clases del paquete completo.')
                    for group in children(diagrams[0], 'elements'):
                        for item in children(group, 'element'):
                            geometry = dict(part.split('=', 1) for part in item.get('geometry', '').split(';') if '=' in part)
                            if 'Left' not in geometry or 'Top' not in geometry:
                                continue
                            try:
                                x, y = float(geometry['Left']), float(geometry['Top'])
                                if not all(math.isfinite(v) and abs(v) <= 100000 for v in (x, y)):
                                    raise ValueError()
                                ea_positions[item.get('subject')] = {'x': x, 'y': y}
                            except ValueError:
                                warnings.append('Una posición de EA inválida se reemplazó por la cuadrícula.')
                for elements_group in children(ext, 'elements'):
                    for item in children(elements_group, 'element'):
                        item_type = xattr(item, 'type') or item.get('type', '')
                        props = children(item, 'properties')
                        s_type = props[0].get('sType', '') if props else ''
                        if item_type.endswith(('PrimitiveType', 'DataType')) or s_type in {'PrimitiveType', 'DataType'}:
                            ref_id = xattr(item, 'idref') or item.get('idref') or xattr(item, 'id')
                            pname = item.get('name', '').strip()
                            if ref_id and pname:
                                ea_primitives[ref_id] = ALIASES.get(pname, pname)
                        for attrs_group in children(item, 'attributes'):
                            for attr in children(attrs_group, 'attribute'):
                                attr_id = xattr(attr, 'idref') or attr.get('idref') or xattr(attr, 'id')
                                attr_props = children(attr, 'properties')
                                if attr_id and attr_props and attr_props[0].get('type'):
                                    tname = attr_props[0].get('type', '').strip()
                                    ea_attribute_types[attr_id] = ALIASES.get(tname, tname)
                for catalog in children(ext, 'primitivetypes'):
                    for primitive in semantic_elements(catalog):
                        if kind(primitive) not in {'PrimitiveType', 'DataType'}:
                            continue
                        pid = xattr(primitive, 'id')
                        if not pid:
                            raise XMIError('Tipo primitivo de EA sin xmi:id')
                        name = primitive.get('name', '').strip()
                        name = ALIASES.get(name, name)
                        if pid in ea_primitives and ea_primitives[pid] != name:
                            raise XMIError(f'Declaraciones primitivas de EA incompatibles: {pid[:100]}')
                        if pid in index and (kind(index[pid]) not in {'PrimitiveType', 'DataType'} or
                                ALIASES.get(index[pid].get('name', '').strip(), index[pid].get('name', '').strip()) != name):
                            raise XMIError(f'El catálogo primitivo de EA contradice el modelo UML: {pid[:100]}')
                        ea_primitives[pid] = name
    model_elements = list(semantic_elements(model))
    class_elements = [e for e in model_elements if kind(e) in {'Class', 'Interface', 'Enumeration', 'AssociationClass'}
                      and not any(kind(p) in {'ClassifierTemplateParameter', 'TemplateParameter'} for p in e.iterancestors())]
    if not class_elements:
        warnings.append('El modelo no contiene clases importables. Aplicarlo dejará el lienzo vacío.')
    if len(class_elements) > 200:
        raise XMIError('El modelo supera el límite de 200 clases')
    ignored = Counter(kind(e) for e in model_elements if local(e) == 'packagedElement'
                      and kind(e) not in {'Class', 'Interface', 'Enumeration', 'Package', 'PrimitiveType', 'Association', 'Dependency', 'Realization', 'InterfaceRealization', 'AssociationClass'})
    if ignored:
        warnings.append('Elementos fuera del perfil omitidos: ' + ', '.join(f'{k} ({v})' for k, v in sorted(ignored.items())))
    if any(local(e) in {'ownedComment', 'ownedRule', 'profileApplication'} for e in model_elements):
        warnings.append('Comentarios, restricciones y perfiles aplicados no se representan en el lienzo.')

    def identifier(element):
        value = xattr(element, 'id')
        if not value:
            raise XMIError(f'{kind(element)} sin xmi:id')
        return value

    def canvas_id(element, category):
        xid = identifier(element)
        meta = extension.get((category, xid))
        if meta is not None and meta.get('canvasId'):
            return meta.get('canvasId')
        prefix = 'n_' if category == 'node' else 'e_'
        return prefix + hashlib.sha256(xid.encode()).hexdigest()[:32]

    ids = {identifier(e): canvas_id(e, 'node') for e in class_elements}
    names = {}
    packages = {}
    for cls in class_elements:
        parts = [p.get('name', '') for p in reversed(list(cls.iterancestors()))
                 if kind(p) == 'Package' and xattr(p, 'id') not in container_ids]
        package = '.'.join(parts) or 'com.example.model'
        packages[identifier(cls)] = package
        names[identifier(cls)] = package + '.' + cls.get('name', '')

    builtins = {t.value for t in UMLSupportedType}
    template_names, signatures, parameters_by_class = {}, {}, {}
    for cls in class_elements:
        parameters_by_class[identifier(cls)] = []
        for signature in children(cls, 'ownedTemplateSignature'):
            if identifier(cls) in signatures.values():
                raise XMIError('Solo se admite una firma de plantilla por clase')
            signatures[identifier(signature)] = identifier(cls)
            params = children(signature, 'ownedParameter')
            if not params:
                raise XMIError('La firma de plantilla requiere parámetros explícitos')
            for param in params:
                if children(param, 'default') or reference(param, 'default') or children(param, 'ownedDefault') or reference(param, 'constrainingClassifier'):
                    raise XMIError('Valores predeterminados y restricciones de parámetros de plantilla no soportados')
                owned = children(param, 'ownedParameteredElement')
                parametered = reference(param, 'parameteredElement') or (identifier(owned[0]) if len(owned) == 1 else None)
                if parametered not in index or kind(param) != 'ClassifierTemplateParameter':
                    raise XMIError('Se requieren parámetros de plantilla de tipo clasificador resolubles')
                name = index[parametered].get('name', '')
                template_names[parametered] = name
                template_names[identifier(param)] = name
                parameters_by_class[identifier(cls)].append(name)
    def resolve_type(element, *, allow_void=False):
        ref = type_reference(element)
        nested = children(element, 'type')
        if not ref and nested:
            href = nested[0].get('href', '')
            if href:
                fragment = href.rsplit('#', 1)[-1]
                if '#' in href and fragment in builtins | set(ALIASES):
                    return ALIASES.get(fragment, fragment)
                # EA 17 can write Real as UML UnlimitedNatural in the semantic
                # section, while retaining Real in attribute metadata. Repair
                # only this evidenced mismatch; UnlimitedNatural is not Real.
                declared = ea_attribute_types.get(xattr(element, 'id'))
                if href == 'http://schema.omg.org/spec/UML/2.1/uml.xml#UnlimitedNatural' and declared == 'Double':
                    warnings.append(f"{element.getparent().get('name', '')}.{element.get('name', '')}: EA declara UnlimitedNatural en UML y Real/Double en sus metadatos; se importa como Double. Revisa el tipo en EA.")
                    return 'Double'
                raise XMIError('Referencia externa de tipo no soportada; no se descargan recursos externos')
        if ref in names:
            return names[ref]
        if ref in template_names:
            return template_names[ref]
        if ref in index and kind(index[ref]) == 'PrimitiveType':
            name = index[ref].get('name', '')
        elif ref in ea_primitives:
            name = ea_primitives[ref]
        elif xattr(element, 'id') in ea_attribute_types:
            name = ea_attribute_types[xattr(element, 'id')]
        elif ref in doc_elements and doc_elements[ref].get('name'):
            name = doc_elements[ref].get('name')
        elif ref in index:
            name = index[ref].get('name', '')
        else:
            name = ref or ''
        name = name.strip()
        name = ALIASES.get(name, name)
        if name in builtins or (allow_void and name == 'void') or name in names.values() or name in set(template_names.values()):
            return name
        raise XMIError(f'Tipo no soportado o referencia sin resolver: {name[:100]}')

    visibility = {v: k for k, v in VISIBILITY.items()}
    def visible(element):
        value = element.get('visibility', 'public')
        if value not in visibility:
            raise XMIError('Visibilidad UML no soportada')
        return visibility[value]

    association_elements = [e for e in model_elements if kind(e) in {'Association', 'AssociationClass'}]
    end_ids = {ref for assoc in association_elements for ref in assoc.get('memberEnd', '').split()}
    for assoc in association_elements:
        end_ids.update(xattr(e, 'idref') for e in children(assoc, 'memberEnd'))
    nodes, edges = [], []
    for offset, cls in enumerate(class_elements):
        xid = identifier(cls)
        attrs, methods = [], []
        for prop in children(cls, 'ownedAttribute'):
            if prop.get('association') or xattr(prop, 'id') in end_ids:
                continue
            cardinality = multiplicity(prop)
            if cardinality not in ('0..1', '1'):
                raise XMIError('Los atributos multivaluados requieren una relación; no se pueden convertir sin pérdida')
            default = children(prop, 'defaultValue')
            default_value = None
            if default:
                if kind(default[0]) == 'OpaqueExpression' and len(children(default[0], 'body')) == 1:
                    default_value = children(default[0], 'body')[0].text or ''
                elif kind(default[0]) in {'LiteralString', 'LiteralInteger', 'LiteralReal', 'LiteralBoolean', 'LiteralUnlimitedNatural'}:
                    default_value = default[0].get('value', '')
                else:
                    raise XMIError('Expresión de valor por defecto no soportada')
            meta = extension.get(('attribute', xattr(prop, 'id')))
            attrs.append(dict(name=prop.get('name', ''), type=resolve_type(prop), visibility=visible(prop),
                is_static=boolean(prop.get('isStatic')), is_nullable=cardinality == '0..1',
                default_value=default_value,
                is_pk=boolean(meta.get('isPk')) if meta is not None else False,
                is_unique=boolean(meta.get('isUnique')) if meta is not None else False))
        for operation in children(cls, 'ownedOperation'):
            params, returns = [], []
            for param in children(operation, 'ownedParameter'):
                direction = param.get('direction', 'in')
                if multiplicity(param) != '1':
                    raise XMIError('Parámetros multivaluados u opcionales no soportados')
                if direction == 'return':
                    returns.append(resolve_type(param, allow_void=True))
                elif direction == 'in':
                    params.append({'name': param.get('name', ''), 'param_type': resolve_type(param)})
                else:
                    raise XMIError('Parámetros out/inout no soportados')
            if len(returns) > 1:
                raise XMIError('Operación con varios retornos no soportada')
            methods.append(dict(name=operation.get('name', ''), return_type=returns[0] if returns else 'void',
                visibility=visible(operation), is_static=boolean(operation.get('isStatic')),
                is_abstract=boolean(operation.get('isAbstract')), parameters=params))
        meta = extension.get(('node', xid))
        position = ea_positions.get(xid, {'x': 60 + offset % 4 * 300, 'y': 60 + offset // 4 * 240})
        if meta is not None:
            try:
                position = {'x': float(meta.get('x', '0')), 'y': float(meta.get('y', '0'))}
            except ValueError:
                raise XMIError('Posición del lienzo inválida') from None
        kind_map = {'Class': 'class', 'Interface': 'interface', 'Enumeration': 'enumeration', 'AssociationClass': 'class'}
        nodes.append(dict(id=ids[xid], position=position, data=dict(name=cls.get('name', ''),
            package_name=packages[xid], kind=kind_map.get(kind(cls), 'class'),
            literals=[lit.get('name', '') for lit in children(cls, 'ownedLiteral')],
            template_parameters=parameters_by_class[xid],
            is_abstract=boolean(cls.get('isAbstract')), attributes=attrs, methods=methods)))
        for general in children(cls, 'generalization'):
            target = general.get('general')
            if target not in ids:
                raise XMIError('Superclase ausente o no soportada')
            edges.append(dict(id=canvas_id(general, 'edge'), source=ids[xid], target=ids[target], type='generalization'))
    for assoc in association_elements:
        refs = assoc.get('memberEnd', '').split()
        if not refs:
            refs = [xattr(e, 'idref') for e in children(assoc, 'memberEnd')]
        if not refs:
            refs = [identifier(e) for e in children(assoc, 'ownedEnd')]
        if len(refs) != 2 or len(set(refs)) != 2 or any(ref not in index for ref in refs):
            raise XMIError('Se requieren asociaciones binarias con extremos resolubles')
        ends = [index[ref] for ref in refs]
        if any(type_reference(end) not in ids for end in ends):
            raise XMIError('Extremo de asociación sin clase soportada')
        aggregation = [end.get('aggregation', 'none') for end in ends]
        if any(value not in {'none', 'shared', 'composite'} for value in aggregation) or sum(v != 'none' for v in aggregation) > 1:
            raise XMIError('Agregación de extremos no soportada')
        relation = 'association_class' if kind(assoc) == 'AssociationClass' else 'association'
        if relation == 'association_class' and any(v != 'none' for v in aggregation):
            raise XMIError('AssociationClass con agregación no soportada')
        if aggregation[1] != 'none':
            ends.reverse(); aggregation.reverse()
        if aggregation[0] != 'none':
            relation = 'composition' if aggregation[0] == 'composite' else 'aggregation'
        source_end, target_end = ends[1], ends[0]
        meta = extension.get(('edge', identifier(assoc)))
        edges.append(dict(id=canvas_id(assoc, 'edge'), source=ids[type_reference(source_end)], target=ids[type_reference(target_end)],
            type=relation, source_cardinality=multiplicity(source_end), target_cardinality=multiplicity(target_end),
            source_role=source_end.get('name') or None, target_role=target_end.get('name') or None,
            relation_name=meta.get('relationName') if meta is not None else assoc.get('name') or None,
            association_node_id=ids[identifier(assoc)] if relation == 'association_class' else None))
    for dependency in (e for e in model_elements if kind(e) in {'Dependency', 'Realization', 'InterfaceRealization'}):
        source, target = reference(dependency, 'client'), reference(dependency, 'supplier')
        if kind(dependency) == 'InterfaceRealization':
            source = source or xattr(dependency.getparent(), 'id')
            target = target or reference(dependency, 'contract')
        if source not in ids or target not in ids:
            raise XMIError('La dependencia debe conectar exactamente dos clases importables')
        edges.append(dict(id=canvas_id(dependency, 'edge'), source=ids[source], target=ids[target],
                          type='dependency' if kind(dependency) == 'Dependency' else 'realization', relation_name=dependency.get('name') or None))
    for binding in (e for e in model_elements if kind(e) == 'TemplateBinding' or local(e) == 'templateBinding'):
        source = xattr(binding.getparent(), 'id')
        signature_id = reference(binding, 'signature')
        target = signatures.get(signature_id)
        if source not in ids or target not in ids:
            raise XMIError('Template binding sin origen o firma de destino resoluble')
        arguments = {}
        formal_ids = {identifier(p) for p in children(index[signature_id], 'ownedParameter')}
        for substitution in children(binding, 'parameterSubstitution'):
            formal, actual = reference(substitution, 'formal'), reference(substitution, 'actual')
            if formal not in formal_ids or actual not in index:
                raise XMIError('Sustitución de plantilla sin parámetro o tipo resoluble')
            name = template_names[formal]
            if name in arguments:
                raise XMIError('Sustitución de parámetro duplicada')
            if actual in names:
                arguments[name] = names[actual]
            elif actual in template_names:
                arguments[name] = template_names[actual]
            elif kind(index[actual]) == 'PrimitiveType':
                raw = index[actual].get('name', '')
                arguments[name] = ALIASES.get(raw, raw)
            else:
                raise XMIError('Tipo de sustitución de plantilla no soportado')
        if set(arguments) != set(parameters_by_class[target]):
            raise XMIError('La vinculación requiere una sustitución por cada parámetro de plantilla')
        meta = extension.get(('edge', identifier(binding)))
        edges.append(dict(id=canvas_id(binding, 'edge'), source=ids[source], target=ids[target],
                          type='template_binding', template_arguments=arguments,
                          relation_name=meta.get('relationName') if meta is not None else None))
    warnings.append('Las extensiones visuales de EA se importan parcialmente: posiciones del primer diagrama de clases; estilos, tamaños y rutas de conectores no se conservan. Las clases sin posición usan una cuadrícula.')
    warnings.append('Navegabilidad, orden, restricciones y semántica de colecciones no forman parte del perfil del editor.')
    try:
        document = UMLCanvasDiagram.model_validate({'nodes': nodes, 'edges': edges})
    except ValidationError as exc:
        messages = '; '.join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise XMIError('El modelo no cumple el perfil del editor: ' + messages[:2000]) from None
    return document, list(dict.fromkeys(warnings))
