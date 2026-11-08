from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

def render(contract: dict, project_id: str | None = None) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    manifest_path = BASE / 'template-manifest.json'
    
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for path in manifest.get('files', []):
            target_file = BASE / 'template' / path
            if target_file.exists():
                files[path] = target_file.read_bytes()
            else:
                # Si es un binario como gradle-wrapper.jar ignorado por git, colocar placeholder vacío
                if path.endswith('.jar'):
                    files[path] = b''
                else:
                    files[path] = b''
    else:
        # Si no existe manifest, recorrer el directorio template
        template_dir = BASE / 'template'
        if template_dir.exists():
            for p in template_dir.rglob('*'):
                if p.is_file():
                    rel_path = str(p.relative_to(template_dir)).replace('\\', '/')
                    files[rel_path] = p.read_bytes()

    # Inyectar el contrato generado
    files['assets/mobile-contract.json'] = json.dumps(contract, indent=2).encode('utf-8')
    return files