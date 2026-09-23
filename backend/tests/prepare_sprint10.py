"""Build both demonstration artifacts without starting platform services."""
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
    models = {'cliente-pedido': json.loads((root / 'exports/cliente-pedido.json').read_text(encoding='utf-8')),
              'taller': workshop()}
    for name, data in models.items():
        target = root / 'exports' / ('sprint-10-' + name)
        raw, _ = generate_solution(UMLCanvasDiagram.model_validate(data), name)
        target.with_suffix('.zip').write_bytes(raw)
        with ZipFile(BytesIO(raw)) as archive:
            archive.extractall(target)
        print(target)
