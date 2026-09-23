"""Explicit Gemini vision check using exports/DC1.png; never writes a project.

Run from backend: .venv/Scripts/python.exe tests/smoke_dc1.py
Requires configured Gemini credentials; sends this image to the configured provider.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from app.schemas.uml import UMLCanvasDiagram
from app.services.ai.gemini import propose
from app.services.ai.tool_caller import build_preview


async def main():
    exports = Path(__file__).resolve().parents[2] / 'exports'
    original = UMLCanvasDiagram()
    try:
        result = await propose(original,
            'Digitaliza el diagrama de clases de esta imagen y agrega sus clases, atributos, métodos y relaciones al canvas.',
            [('image/png', (exports / 'DC1.png').read_bytes())])
        preview = build_preview(original, result)
    except HTTPException as exc:
        print(f'ERROR CONTROLADO {exc.status_code}: {exc.detail}')
        return 1
    output = {'document': preview['document'].model_dump(mode='json'),
              'message': result.message, 'warnings': result.warnings}
    (exports / 'DC1-propuesta-gemini.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Clases:', ', '.join(n.data.name for n in preview['document'].nodes))
    print('Relaciones:', len(preview['document'].edges))
    print('Avisos:', json.dumps(result.warnings, ensure_ascii=True))
    print('Propuesta validada guardada en exports/DC1-propuesta-gemini.json; sin modificar proyectos.')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
