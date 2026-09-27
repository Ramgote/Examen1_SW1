"""Create cloud configuration on the server without printing credentials."""
import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import urlsplit


def main():
    target = Path(__file__).resolve().parent / '.env'
    if target.exists():
        sys.exit('Ya existe deploy/.env. Se conserva para no cambiar las claves de la base de datos.')
    raw = input('Dominio o IP publica del servidor (sin rutas): ').strip()
    if '://' not in raw:
        try:
            ipaddress.IPv4Address(raw)
            raw = 'http://' + raw
        except ValueError:
            raw = 'https://' + raw
    url = urlsplit(raw)
    if (url.scheme not in ('http', 'https') or not url.hostname
            or url.username or url.password or url.port
            or url.path not in ('', '/') or url.query or url.fragment
            or not re.fullmatch(r'[A-Za-z0-9.-]+', url.hostname)):
        sys.exit('Direccion invalida. Introduce solo el dominio o la IPv4 publica.')
    origin = f'{url.scheme}://{url.hostname}'
    gemini = getpass.getpass('Clave Gemini (oculta; Enter para configurar despues): ').strip()
    if gemini and not re.fullmatch(r'[A-Za-z0-9_-]+', gemini):
        sys.exit('Formato de clave Gemini invalido.')
    model = input('Modelo Gemini [gemini-3.6-flash]: ').strip() or 'gemini-3.6-flash'
    if not re.fullmatch(r'gemini-[A-Za-z0-9.-]+', model):
        sys.exit('Modelo invalido.')
    values = {
        'SITE_ADDRESS': origin,
        'PUBLIC_IP': url.hostname,
        'POSTGRES_USER': 'uml',
        'POSTGRES_PASSWORD': secrets.token_hex(32),
        'POSTGRES_DB': 'uml_platform_db',
        'SECRET_KEY': secrets.token_hex(48),
        'BACKEND_CORS_ORIGINS': json.dumps([origin]),
        'GEMINI_API_KEY': gemini,
        'GEMINI_MODEL': model,
        'AI_TIMEOUT_SECONDS': '60',
    }
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as output:
        output.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    print(f'Configuracion guardada. Direccion de la aplicacion: {origin}')


if __name__ == '__main__':
    main()
