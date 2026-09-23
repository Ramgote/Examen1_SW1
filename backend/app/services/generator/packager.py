from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import json
import hashlib
from app.services.generator.spring_boot.renderer import render
from app.services.generator.flutter.renderer import render as render_flutter


def generate_spring(diagram):
    files, warnings = render(diagram)
    return package(files), warnings


def package(files):
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            if PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or '\\' in path:
                raise ValueError('Ruta de artefacto inválida')
            info = ZipInfo(path)
            info.create_system = 3
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (0o100755 if PurePosixPath(path).name == 'gradlew' else 0o100644) << 16
            archive.writestr(info, content if isinstance(content, bytes) else content.encode('utf-8'))
    return output.getvalue()


def generate_solution(diagram, project_id='example'):
    backend, warnings = render(diagram)
    contract = json.loads(backend['mobile-contract.json'])
    mobile = render_flutter(contract, project_id)
    files = {**{'backend/' + p: v for p, v in backend.items()},
             **{'mobile/' + p: v for p, v in mobile.items()}}
    manifest = {'generator': 'solution-v1', 'canvas_version': diagram.version,
                'project_id': str(project_id), 'contract_fingerprint': contract['fingerprint'],
                'model_sha256': hashlib.sha256(backend['model.json'].encode()).hexdigest(),
                'mobile_platforms': ['android'], 'local_stt': True,
                'warnings': warnings}
    files['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2)
    files['README.md'] = '''# Spring Boot + Flutter desde un mismo diagrama UML

backend/ contiene Java 21 Maven, PostgreSQL y CRUD REST con metadatos de contrato.
mobile/ contiene Flutter Android con modelos tipados, cliente HTTP y Asistente de Voz y Texto local.
Ambos proyectos comparten exactamente el mismo contrato (mobile-contract.json).
manifest.json identifica proyecto, versión del canvas, huella SHA-256 y capacidades locales.

## Puesta en marcha rápida:
1. Sigue backend/README.md para iniciar PostgreSQL y Spring Boot (puerto 8080).
   Usa una base de datos independiente por modelo.
2. Sigue mobile/README.md para compilar e instalar la app Flutter en tu dispositivo.
3. En Ajustes de la app móvil ingresa la URL de la API (ej. http://192.168.1.51:8080/api).
4. Comprueba conexión y opera el sistema mediante texto o dictando comandos por voz.
'''
    return package(files), warnings
