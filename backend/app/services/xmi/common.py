"""Names and limits for the supported UML class interchange profile."""
from lxml import etree

XMI = 'http://www.omg.org/spec/XMI/20131001'
UML = 'http://www.omg.org/spec/UML/20131001'
PLATFORM = 'urn:uml-platform:canvas:1'
MAX_BYTES = 4 * 1024 * 1024
VISIBILITY = {'+': 'public', '-': 'private', '#': 'protected', '~': 'package'}


class XMIError(ValueError):
    pass


def tag(namespace, name):
    return f'{{{namespace}}}{name}'


def child(parent, element_name, *, id=None, kind=None, **attrs):
    if id is not None:
        attrs[tag(XMI, 'id')] = id
    if kind is not None:
        attrs[tag(XMI, 'type')] = 'uml:' + kind
    return etree.SubElement(parent, element_name, {k: str(v) for k, v in attrs.items() if v is not None})


def bounds(parent, multiplicity):
    lower, upper = ('0', '*') if multiplicity == '*' else (
        multiplicity.split('..') if '..' in multiplicity else (multiplicity, multiplicity))
    child(parent, 'lowerValue', kind='LiteralInteger', value=lower)
    child(parent, 'upperValue', kind='LiteralUnlimitedNatural', value=upper)
