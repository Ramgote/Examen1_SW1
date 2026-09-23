"""Sprint 12: Build both demonstration artifacts (Cliente-Pedido and Taller) with final Sprint 11 voice capabilities."""
from pathlib import Path
import sys
import json
from io import BytesIO
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.uml import UMLCanvasDiagram
from app.services.generator.packager import generate_solution
from test_sprint10 import workshop

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    models = {
        'cliente-pedido': json.loads((root / 'exports/cliente-pedido.json').read_text(encoding='utf-8')),
        'taller': workshop(),
    }
    for name, data in models.items():
        target = root / 'exports' / ('sprint-12-' + name)
        raw, warnings = generate_solution(UMLCanvasDiagram.model_validate(data), name)
        zip_path = target.with_suffix('.zip')
        zip_path.write_bytes(raw)
        with ZipFile(BytesIO(raw)) as archive:
            archive.extractall(target)
        print(f"Generated and extracted: {zip_path} ({len(raw)} bytes, {len(warnings)} warnings)")
