"""Build a source-only upload bundle; exclude local credentials and caches."""
from pathlib import Path
import os
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'scratch' / 'uml-cloud.tar.gz'
SKIP = {'node_modules', 'dist', '__pycache__', '.venv', 'venv', '.git',
        '.pytest_cache', '.mypy_cache', 'tests'}


def allowed(path):
    return (not path.is_symlink() and not any(part in SKIP for part in path.parts)
            and not path.name.startswith('.env')
            and path.suffix.lower() not in {'.pem', '.key', '.pyc', '.log', '.tar', '.gz', '.zip'})


def main():
    DEST.parent.mkdir(exist_ok=True)
    with tarfile.open(DEST, 'w:gz') as bundle:
        bundle.add(ROOT / 'compose.cloud.yml', arcname='compose.cloud.yml')
        bundle.add(ROOT / 'compose.cloud-https-ip.yml', arcname='compose.cloud-https-ip.yml')
        for folder in ('backend', 'frontend', 'deploy'):
            for directory, children, files in os.walk(ROOT / folder):
                children[:] = sorted(name for name in children if name not in SKIP
                                     and not (Path(directory) / name).is_symlink())
                for name in sorted(files):
                    path = Path(directory) / name
                    relative = path.relative_to(ROOT)
                    if allowed(path):
                        bundle.add(path, arcname=relative.as_posix(), recursive=False)
    print(f'Paquete sin archivos .env: {DEST} ({DEST.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
