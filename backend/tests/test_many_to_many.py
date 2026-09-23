"""Test Case: Many-to-Many relationship (N:M) between two classes.
Verifies that:
1. AST transformer detects ManyToMany on both ends.
2. Spring Boot entity generates @ManyToMany and @JoinTable (creating the 3rd join table in PostgreSQL).
3. Inverse entity generates @ManyToMany(mappedBy = ...).
4. Request/Response DTOs and Services handle Set of related IDs.
5. mobile-contract.json correctly documents the N:M relationship.
"""
import unittest
from app.schemas.uml import UMLCanvasDiagram, UMLClassNode, UMLEdge, UMLClassData, UMLAttribute, CanvasPosition
from app.services.generator.ast_transformer import transform
from app.services.generator.spring_boot.renderer import render
from app.services.generator.contract import build_contract

class ManyToManyTests(unittest.TestCase):
    def setUp(self):
        # Create 2 classes: Estudiante and Curso
        self.diagram = UMLCanvasDiagram(
            version=1,
            nodes=[
                UMLClassNode(
                    id='node_estudiante',
                    type='uml_class',
                    position=CanvasPosition(x=100, y=100),
                    data=UMLClassData(
                        name='Estudiante',
                        package_name='com.example.model',
                        attributes=[
                            UMLAttribute(name='id', type='Long', is_pk=True, is_nullable=False),
                            UMLAttribute(name='nombre', type='String', is_nullable=False),
                            UMLAttribute(name='matricula', type='String', is_unique=True),
                        ],
                    ),
                ),
                UMLClassNode(
                    id='node_curso',
                    type='uml_class',
                    position=CanvasPosition(x=500, y=100),
                    data=UMLClassData(
                        name='Curso',
                        package_name='com.example.model',
                        attributes=[
                            UMLAttribute(name='id', type='Long', is_pk=True, is_nullable=False),
                            UMLAttribute(name='titulo', type='String', is_nullable=False),
                            UMLAttribute(name='creditos', type='Integer', is_nullable=False),
                        ],
                    ),
                ),
            ],
            edges=[
                # Edge: Many-to-Many (* to *)
                UMLEdge(
                    id='edge_estudiante_curso',
                    source='node_estudiante',
                    target='node_curso',
                    type='association',
                    source_cardinality='*',
                    target_cardinality='*',
                    source_role='estudiantes',
                    target_role='cursos',
                    relation_name='inscripcion',
                ),
            ],
        )

    def test_ast_transformer_many_to_many(self):
        plan = transform(self.diagram)
        self.assertEqual(len(plan['classes']), 2)
        
        estudiante = next(c for c in plan['classes'] if c['name'] == 'Estudiante')
        curso = next(c for c in plan['classes'] if c['name'] == 'Curso')

        # Check Estudiante relation (owner of JoinTable)
        rel_estudiante = estudiante['rels'][0]
        self.assertEqual(rel_estudiante['kind'], 'ManyToMany')
        self.assertTrue(rel_estudiante['many'])
        self.assertTrue(rel_estudiante['owner'])
        self.assertTrue(rel_estudiante['join'].startswith('r_'))

        # Check Curso relation (inverse side)
        rel_curso = curso['rels'][0]
        self.assertEqual(rel_curso['kind'], 'ManyToMany')
        self.assertTrue(rel_curso['many'])
        self.assertFalse(rel_curso['owner'])
        self.assertEqual(rel_curso['inverse'], 'cursos')

    def test_spring_boot_entity_generation_with_join_table(self):
        files, warnings = render(self.diagram)

        # 1. Inspect Estudiante.java
        estudiante_java = files['src/main/java/com/generated/entity/Estudiante.java']
        self.assertIn('@ManyToMany(fetch = FetchType.LAZY)', estudiante_java)
        self.assertIn('@JoinTable(name = "r_', estudiante_java)
        self.assertIn('joinColumns = @JoinColumn(name = "owner_id")', estudiante_java)
        self.assertIn('inverseJoinColumns = @JoinColumn(name = "target_id")', estudiante_java)
        self.assertIn('private Set<Curso> cursos = new LinkedHashSet<>();', estudiante_java)

        # 2. Inspect Curso.java
        curso_java = files['src/main/java/com/generated/entity/Curso.java']
        self.assertIn('@ManyToMany(mappedBy = "cursos", fetch = FetchType.LAZY)', curso_java)
        self.assertIn('private Set<Estudiante> estudiantes = new LinkedHashSet<>();', curso_java)

        # 3. Inspect Service / DTOs
        estudiante_req = files['src/main/java/com/generated/dto/EstudianteRequest.java']
        self.assertIn('Set<@NotNull Long> cursosIds', estudiante_req)

        estudiante_resp = files['src/main/java/com/generated/dto/EstudianteResponse.java']
        self.assertIn('Set<Long> cursosIds', estudiante_resp)

        # 4. Inspect Contract
        contract = build_contract(transform(self.diagram))
        self.assertEqual(len(contract['entities']), 2)
        est_contract = next(e for e in contract['entities'] if e['name'] == 'Estudiante')
        self.assertIn('cursos', [r['name'] for r in est_contract['relationships']])
        rel = next(r for r in est_contract['relationships'] if r['name'] == 'cursos')
        self.assertTrue(rel['many'])
        self.assertEqual(rel['entity'], 'Curso')
        self.assertEqual(rel['field'], 'cursosIds')


if __name__ == '__main__':
    unittest.main()
