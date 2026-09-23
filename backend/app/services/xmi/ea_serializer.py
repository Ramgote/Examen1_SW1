"""EA17-targeted XMI 2.1 class profile, retaining the EA15 exchange structure.

Structural compatibility is tested; rendering must also be checked inside EA.
"""
from uuid import UUID, uuid5
from lxml import etree
from app.services.xmi.common import XMI, UML, PLATFORM, tag
from app.services.xmi.serializer import serialize_xmi

EA_XMI = 'http://schema.omg.org/spec/XMI/2.1'
EA_UML = 'http://schema.omg.org/spec/UML/2.1'


def serialize_ea_xmi(document, project_id: UUID, project_name='Diagrama de clases'):
    root = etree.fromstring(serialize_xmi(document))
    model = root.find(tag(UML, 'Model'))
    model.set(tag(XMI, 'type'), 'uml:Model')
    extension = root.find(tag(XMI, 'Extension'))

    def guid(key, package=False):
        return ('EAPK_' if package else 'EAID_') + str(uuid5(project_id, key)).replace('-', '_').upper()

    # A single exportable package contains all semantics, including shared types.
    container = etree.Element('packagedElement', {tag(XMI, 'type'): 'uml:Package',
        tag(XMI, 'id'): 'export_container', 'name': 'Modelo', 'visibility': 'public'})
    for item in list(model):
        container.append(item)
    model.append(container)
    etree.SubElement(extension, tag(PLATFORM, 'container'), ref='export_container')
    id_map = {}
    for offset, element in enumerate(root.iter()):
        if element.tag.startswith('{' + PLATFORM + '}'):
            continue
        if element.get(tag(XMI, 'type')) or element is model:
            if element.get(tag(XMI, 'id')) is None:
                element.set(tag(XMI, 'id'), f'generated_{offset}')
        old_id = element.get(tag(XMI, 'id'))
        if old_id:
            id_map[old_id] = guid(old_id, element.get(tag(XMI, 'type')) == 'uml:Package')
    for element in root.iter():
        for key, value in list(element.attrib.items()):
            if key == tag(XMI, 'id'):
                element.set(key, id_map[value])
            elif key in {tag(XMI, 'idref'), 'type', 'general', 'client', 'supplier', 'association', 'memberEnd', 'ref', 'signature', 'formal', 'actual', 'parameteredElement'}:
                element.set(key, ' '.join(id_map.get(ref, ref) for ref in value.split()))
    # Use the same nested references and repeated memberEnd representation as EA15.
    for element in list(model.iter()):
        ref = element.attrib.pop('type', None)
        if ref:
            etree.SubElement(element, 'type', {tag(XMI, 'idref'): ref})
        members = element.attrib.pop('memberEnd', None)
        if members:
            for ref in members.split():
                etree.SubElement(element, 'memberEnd', {tag(XMI, 'idref'): ref})
        if element.get(tag(XMI, 'type')) == 'uml:LiteralUnlimitedNatural' and element.get('value') == '*':
            element.set('value', '-1')
    # Rebuild namespace declarations instead of only changing the visible prefixes.
    def convert(element):
        def converted(name):
            return name.replace('{' + XMI + '}', '{' + EA_XMI + '}').replace('{' + UML + '}', '{' + EA_UML + '}')
        result = etree.Element(converted(element.tag),
            {converted(k): v for k, v in element.attrib.items()})
        result.text = element.text
        for item in element:
            result.append(convert(item))
        return result
    output = etree.Element(tag(EA_XMI, 'XMI'), nsmap={'xmi': EA_XMI, 'uml': EA_UML, 'platform': PLATFORM})
    output.set(tag(EA_XMI, 'version'), '2.1')
    # EA uses this dialect marker to select its extended importer. Keep our
    # provenance in our extension; the standard exporter remains UMLPlatform.
    etree.SubElement(output, tag(EA_XMI, 'Documentation'), exporter='Enterprise Architect', exporterVersion='6.5')
    for item in root:
        if item.tag == tag(UML, 'Model'):
            output.append(convert(item))
    model_id = id_map['model']
    package_id = id_map['export_container']
    ea = etree.SubElement(output, tag(EA_XMI, 'Extension'), extender='Enterprise Architect', extenderID='6.5')
    elements = etree.SubElement(ea, 'elements')
    for element in output.find(tag(EA_UML, 'Model')).iter('packagedElement'):
        kind = element.get(tag(EA_XMI, 'type'), '').split(':')[-1]
        if kind not in {'Class', 'Interface', 'Enumeration', 'Package', 'PrimitiveType'}:
            continue
        item = etree.SubElement(elements, 'element', {tag(EA_XMI, 'idref'): element.get(tag(EA_XMI, 'id')),
            tag(EA_XMI, 'type'): 'uml:' + kind, 'name': element.get('name', ''), 'scope': 'public'})
        parent_id = element.getparent().get(tag(EA_XMI, 'id'), model_id)
        etree.SubElement(item, 'model', package=parent_id)
        etree.SubElement(item, 'properties', sType=kind, isAbstract=element.get('isAbstract', 'false'))
    connectors = etree.SubElement(ea, 'connectors')
    for edge in document.model_dump(mode='json')['edges']:
        connector = etree.SubElement(connectors, 'connector', {tag(EA_XMI, 'idref'): id_map['e_' + edge['id']]})
        if edge['relation_name']:
            connector.set('name', edge['relation_name'])
        for side in ('source', 'target'):
            end = etree.SubElement(connector, side, {tag(EA_XMI, 'idref'): id_map['n_' + edge[side]]})
            role = etree.SubElement(end, 'role', visibility='Public', targetScope='instance')
            if edge[side + '_role']:
                role.set('name', edge[side + '_role'])
            aggregation = ('composite' if edge['type'] == 'composition' else 'shared') if side == 'source' and edge['type'] in {'composition', 'aggregation'} else 'none'
            etree.SubElement(end, 'type', multiplicity=edge[side + '_cardinality'], aggregation=aggregation, containment='Unspecified')
        ea_type = {'generalization': 'Generalization', 'dependency': 'Dependency', 'realization': 'Realisation',
                   'association_class': 'AssociationClass', 'template_binding': 'TemplateBinding'}.get(edge['type'], 'Association')
        etree.SubElement(connector, 'properties', ea_type=ea_type, direction='Unspecified')
        etree.SubElement(connector, 'appearance', linemode='3', linecolor='-1', linewidth='0')
    diagrams = etree.SubElement(ea, 'diagrams')
    diagram = etree.SubElement(diagrams, 'diagram', {tag(EA_XMI, 'id'): guid('class_diagram')})
    etree.SubElement(diagram, 'model', package=package_id, owner=package_id)
    etree.SubElement(diagram, 'properties', name=project_name, type='Logical')
    etree.SubElement(diagram, 'project', author='UMLPlatform', version='1.0')
    etree.SubElement(diagram, 'style1', value='ShowPrivate=1;ShowProtected=1;ShowPublic=1;HideRelationships=0;HideAtts=0;HideOps=0;')
    etree.SubElement(diagram, 'style2', value='MDGDgm=;ShowNotes=0;ShowOpRetType=1;')
    etree.SubElement(diagram, 'extendedProperties')
    objects = etree.SubElement(diagram, 'elements')
    min_x = min((n.position.x for n in document.nodes), default=0)
    min_y = min((n.position.y for n in document.nodes), default=0)
    for order, node in enumerate(document.nodes, 1):
        left = round(node.position.x - min_x + 40)
        top = round(node.position.y - min_y + 40)
        height = round(node.height) if node.height else 80 + 22 * (len(node.data.attributes) + len(node.data.methods))
        width = round(node.width) if node.width else 260
        etree.SubElement(objects, 'element', subject=id_map['n_' + node.id], seqno=str(order),
            geometry=f'Left={left};Top={top};Right={left + width};Bottom={top + height};')
    for edge in document.edges:
        etree.SubElement(objects, 'element', subject=id_map['e_' + edge.id],
                         geometry='SX=0;SY=0;EX=0;EY=0;', style='Mode=3;Color=-1;LWidth=0;Hidden=0;')
    output.append(convert(extension))
    output[-1].set('generator', 'UMLPlatform')
    return etree.tostring(output, encoding='UTF-8', xml_declaration=True, pretty_print=True)
