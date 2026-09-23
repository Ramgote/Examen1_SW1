"""Prepare a synthetic generated project for real Maven/PostgreSQL verification."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.uml import UMLCanvasDiagram
from app.services.generator.spring_boot.renderer import render


def smoke_model():
    def node(name, attrs=None, abstract=False):
        return {'id': name, 'position': {'x': 0, 'y': 0}, 'data': {
            'name': name, 'is_abstract': abstract, 'attributes': attrs or []}}
    def attr(name, kind='String', **kwargs):
        return {'name': name, 'type': kind, **kwargs}
    def edge(source, target, source_role, target_role, sc='1', tc='*', kind='association'):
        return dict(id=source + target, source=source, target=target, source_role=source_role,
                    target_role=target_role, source_cardinality=sc, target_cardinality=tc, type=kind)
    return UMLCanvasDiagram.model_validate({'nodes': [
        node('Cliente', [attr('nombre', is_nullable=False, is_unique=True)]),
        node('Pedido', [attr('total', 'BigDecimal', is_nullable=False)]),
        node('Producto', [attr('codigo', is_pk=True), attr('precio', 'Double')]),
        node('Etiqueta'), node('Perfil'),
        node('Persona', [attr('nombre')], True), node('Empleado', [attr('salario', 'BigDecimal')]),
        node('Tipos', [attr('numero', 'Integer'), attr('largo', 'Long'), attr('real', 'Float'),
                       attr('activo', 'Boolean'), attr('fecha', 'LocalDate'), attr('instante', 'LocalDateTime'), attr('texto', 'Text')]),
    ], 'edges': [edge('Cliente', 'Pedido', 'cliente', 'pedidos', kind='composition'),
                edge('Producto', 'Etiqueta', 'productos', 'etiquetas', '*', '*'),
                edge('Cliente', 'Perfil', 'cliente', 'perfil', '0..1', '0..1'),
                edge('Empleado', 'Persona', None, None, kind='generalization')]})


if __name__ == '__main__':
    target = Path(__file__).resolve().parents[2] / 'exports' / 'sprint-5-verification'
    files, _ = render(smoke_model())
    for path, content in files.items():
        output = target / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding='utf-8')
    test_target = target / 'src/test/java/com/generated/GeneratedApiTest.java'
    test_target.parent.mkdir(parents=True, exist_ok=True)
    test_target.write_bytes((Path(__file__).parent / 'fixtures' / 'GeneratedApiTest.java').read_bytes())
    print(target)
