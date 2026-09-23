"""Documento canónico del subconjunto de clases UML soportado por la plataforma."""
from enum import Enum
from typing import Annotated, Literal
from collections import Counter
from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')]
ElementId = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')]
TypeName = Annotated[str, Field(min_length=1, max_length=255)]


class UMLModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


class UMLVisibility(str, Enum):
    PUBLIC = '+'
    PRIVATE = '-'
    PROTECTED = '#'
    PACKAGE = '~'


class UMLRelationshipType(str, Enum):
    ASSOCIATION = 'association'
    AGGREGATION = 'aggregation'
    COMPOSITION = 'composition'
    GENERALIZATION = 'generalization'
    DEPENDENCY = 'dependency'
    REALIZATION = 'realization'
    ASSOCIATION_CLASS = 'association_class'
    TEMPLATE_BINDING = 'template_binding'


class UMLSupportedType(str, Enum):
    STRING = 'String'
    INTEGER = 'Integer'
    LONG = 'Long'
    DOUBLE = 'Double'
    FLOAT = 'Float'
    BOOLEAN = 'Boolean'
    BIGDECIMAL = 'BigDecimal'
    DATE = 'LocalDate'
    DATETIME = 'LocalDateTime'
    TEXT = 'Text'


def valid_multiplicity(value):
    if '..' in value:
        lower, upper = value.split('..')
        if upper != '*' and int(lower) > int(upper):
            raise ValueError('La multiplicidad mínima no puede superar la máxima')
    return value


Multiplicity = Annotated[str, Field(max_length=20, pattern=r'^(\*|(?:0|[1-9][0-9]*)(?:\.\.(?:\*|0|[1-9][0-9]*))?)$'), AfterValidator(valid_multiplicity)]


class UMLParameter(UMLModel):
    name: Identifier
    param_type: TypeName


class UMLMethod(UMLModel):
    name: Identifier
    return_type: TypeName = 'void'
    visibility: UMLVisibility = UMLVisibility.PUBLIC
    parameters: list[UMLParameter] = Field(default_factory=list, max_length=30)
    is_static: bool = False
    is_abstract: bool = False


class UMLAttribute(UMLModel):
    name: Identifier
    type: TypeName = 'String'
    visibility: UMLVisibility = UMLVisibility.PRIVATE
    is_pk: bool = False
    is_nullable: bool = True
    is_unique: bool = False
    is_static: bool = False
    default_value: str | None = Field(default=None, max_length=1000)


class UMLClassData(UMLModel):
    template_parameters: list[Identifier] = Field(default_factory=list, max_length=20)
    kind: Literal['class', 'interface', 'enumeration'] = 'class'
    literals: list[Identifier] = Field(default_factory=list, max_length=100)
    name: str = Field(min_length=1, max_length=100, pattern=r'^[A-Z][A-Za-z0-9]*$')
    is_abstract: bool = False
    package_name: str = Field(default='com.example.model', max_length=150,
                              pattern=r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$')
    attributes: list[UMLAttribute] = Field(default_factory=list, max_length=100)
    methods: list[UMLMethod] = Field(default_factory=list, max_length=100)


class CanvasPosition(UMLModel):
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)


class CanvasViewport(CanvasPosition):
    zoom: float = Field(ge=0.1, le=4)


class CanvasMetadata(UMLModel):
    viewport: CanvasViewport | None = None


class UMLClassNode(UMLModel):
    width: float | None = Field(default=None, ge=200, le=10000)
    height: float | None = Field(default=None, ge=110, le=10000)
    id: ElementId
    type: Literal['uml_class'] = 'uml_class'
    position: CanvasPosition
    data: UMLClassData


class UMLEdge(UMLModel):
    template_arguments: dict[Identifier, TypeName] = Field(default_factory=dict, max_length=20)
    source_handle: Literal['source-right', 'source-bottom'] | None = None
    target_handle: Literal['target-left', 'target-top'] | None = None
    id: ElementId
    source: ElementId
    target: ElementId
    type: UMLRelationshipType = UMLRelationshipType.ASSOCIATION
    source_cardinality: Multiplicity = '1'
    target_cardinality: Multiplicity = '*'
    source_role: Identifier | None = None
    target_role: Identifier | None = None
    relation_name: str | None = Field(default=None, max_length=150)

    @model_validator(mode='after')
    def check_multiplicities(self):
        if self.type == UMLRelationshipType.COMPOSITION:
            upper = self.source_cardinality.split('..')[-1]
            if upper == '*' or int(upper) > 1:
                raise ValueError('En composición, el extremo del todo (origen) tiene máximo 1')
        return self


class UMLCanvasDiagram(UMLModel):
    schema_version: Literal[1] = 1
    version: int = Field(default=1, ge=1, le=2147483646, strict=True)
    nodes: list[UMLClassNode] = Field(default_factory=list, max_length=200)
    edges: list[UMLEdge] = Field(default_factory=list, max_length=500)
    metadata: CanvasMetadata = Field(default_factory=CanvasMetadata)

    @model_validator(mode='after')
    def semantic_validation(self):
        def unique(values, label):
            if len(values) != len(set(values)):
                raise ValueError(f'{label}: valores duplicados')
        unique([n.id for n in self.nodes] + [e.id for e in self.edges], 'Identificadores')
        unique([f'{n.data.package_name}.{n.data.name}' for n in self.nodes], 'Clases en el mismo paquete')
        classes = {n.id: n.data for n in self.nodes}
        names = Counter(n.data.name for n in self.nodes)
        qualified = {f'{n.data.package_name}.{n.data.name}' for n in self.nodes}
        builtins = {t.value for t in UMLSupportedType}

        def check_type(value, owner, allow_void=False):
            if value in owner.template_parameters:
                return value
            if value in builtins or (allow_void and value == 'void'):
                return value
            if value in qualified:
                return value
            if f'{owner.package_name}.{value}' in qualified:
                return f'{owner.package_name}.{value}'
            if names[value] == 1:
                return next(f'{n.data.package_name}.{value}' for n in self.nodes if n.data.name == value)
            raise ValueError(f'{owner.name}: tipo desconocido o ambiguo "{value}"')

        for data in classes.values():
            unique(data.template_parameters, f'Parámetros de plantilla de {data.name}')
            unique(data.literals, f'Literales de {data.name}')
            if data.kind != 'enumeration' and data.literals:
                raise ValueError('Solo una enumeración puede contener literales')
            unique([a.name for a in data.attributes], f'Atributos de {data.name}')
            unique([(m.name, tuple(check_type(p.param_type, data) for p in m.parameters)) for m in data.methods], f'Firmas de métodos de {data.name}')
            for attr in data.attributes:
                check_type(attr.type, data)
            for method in data.methods:
                unique([p.name for p in method.parameters], f'Parámetros de {data.name}.{method.name}')
                if method.is_abstract and not data.is_abstract and data.kind != 'interface':
                    raise ValueError(f'{data.name}: una clase con métodos abstractos debe ser abstracta')
                check_type(method.return_type, data, allow_void=True)
                for parameter in method.parameters:
                    check_type(parameter.param_type, data)
        parents = {node_id: [] for node_id in classes}
        for edge in self.edges:
            if edge.template_arguments and edge.type != UMLRelationshipType.TEMPLATE_BINDING:
                raise ValueError('Solo template binding puede contener sustituciones de parámetros')
            if edge.source not in classes or edge.target not in classes:
                raise ValueError(f'Relación {edge.id}: clase de origen o destino inexistente')
            if edge.type == UMLRelationshipType.TEMPLATE_BINDING:
                for actual in edge.template_arguments.values():
                    check_type(actual, classes[edge.source])
            if edge.type == UMLRelationshipType.GENERALIZATION:
                if edge.target in parents[edge.source]:
                    raise ValueError('Generalización duplicada')
                parents[edge.source].append(edge.target)
        visited, visiting = set(), set()
        def visit(node_id):
            if node_id in visiting:
                raise ValueError('La herencia no puede contener ciclos ni generalización a sí misma')
            if node_id in visited:
                return
            visiting.add(node_id)
            for parent in parents[node_id]:
                visit(parent)
            visiting.remove(node_id)
            visited.add(node_id)
        for node_id in classes:
            visit(node_id)
        return self
