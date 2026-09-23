from pathlib import Path
import json
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from app.services.generator.ast_transformer import transform
from app.services.generator.contract import build_contract

BOOT_VERSION = '3.5.16'


def render(diagram):
    plan = transform(diagram)
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / 'templates'),
                      undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True,
                      trim_blocks=True, lstrip_blocks=True)
    files = {}
    contract = json.dumps(build_contract(plan), ensure_ascii=False, indent=2)
    files['mobile-contract.json'] = contract
    files['src/main/resources/mobile-contract.json'] = contract
    def add(path, template, **kwargs):
        files[path] = env.get_template(template).render(**plan, boot_version=BOOT_VERSION, **kwargs)
    add('pom.xml', 'pom.xml.j2')
    add('src/main/resources/application.properties', 'application.properties.j2')
    add('src/main/java/com/generated/Application.java', 'Application.java.j2')
    add('src/main/java/com/generated/api/ApiErrors.java', 'ApiErrors.java.j2')
    add('src/main/java/com/generated/api/ContractController.java', 'ContractController.java.j2')
    add('src/test/java/com/generated/ApplicationContextTest.java', 'ApplicationContextTest.java.j2')
    for c in plan['classes']:
        add(f"src/main/java/com/generated/entity/{c['name']}.java", 'Entity.java.j2', c=c)
        add(f"src/main/java/com/generated/repository/{c['name']}Repository.java", 'Repository.java.j2', c=c)
        if not c['abstract']:
            for layer, suffix, template in [('dto', 'Request', 'Request.java.j2'), ('dto', 'Response', 'Response.java.j2'),
                                            ('service', 'Service', 'Service.java.j2'), ('api', 'Controller', 'Controller.java.j2')]:
                add(f"src/main/java/com/generated/{layer}/{c['name']}{suffix}.java", template, c=c)
    add('README.md', 'README.md.j2')
    add('compose.yaml', 'compose.yaml.j2')
    files['.gitignore'] = 'target/\n.env\n.idea/\n*.iml\n'
    files['model.json'] = diagram.model_dump_json(indent=2)
    files['generation-report.json'] = json.dumps({'generator': 'spring-v1', 'spring_boot': BOOT_VERSION,
        'canvas_version': diagram.version, 'warnings': plan['warnings'],
        'entities': [{'name': c['name'], 'table': c['table'], 'abstract': c['abstract'],
                      'relationships': c['all_rels']} for c in plan['classes']]}, ensure_ascii=False, indent=2)
    return files, plan['warnings']
