# Despliegue de demostración en AWS

Esta variante ejecuta React, FastAPI (un proceso) y PostgreSQL en una EC2.
No utiliza RDS ni los servicios systemd del manual de ayuda.
La base de datos empieza vacía: no copia usuarios ni proyectos locales.
Los datos persisten en un volumen Docker; no ejecutar `down -v`.

## Servidor

- Región: us-east-1.
- Ubuntu Server 24.04 LTS, arquitectura x86_64.
- Instancia: t3.small, 2 GiB RAM, para la demostración.
- Disco: 25 GiB gp3; uso cubierto con créditos según saldo y plan.
- IPv4 pública habilitada.
- SSH 22 solo desde Mi IP. HTTP 80 y HTTPS 443 desde Internet.
- No abrir PostgreSQL 5432 ni FastAPI 8000.
- Conservar la clave .pem fuera del repositorio.

## Dentro de Ubuntu (no en PowerShell)

Instalar Docker y Compose desde los paquetes de Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo docker compose version
```

Una vez transferido y extraído el proyecto, entrar en su carpeta y ejecutar:

```bash
python3 deploy/configure.py
sudo docker compose -f compose.cloud.yml up -d --build
sudo docker compose -f compose.cloud.yml ps -a
```

El asistente pregunta la IP o dominio, crea claves aleatorias y configura el
origen permitido para WebSocket. La clave Gemini se introduce oculta.
Enter permite aplazar Gemini; la aplicación básica funciona sin IA.
Usar el modelo que ya funcione en la cuenta Gemini del proyecto.
No compartir el archivo deploy/.env ni incluirlo en Git.

## Comprobar

Abrir `http://IP_PUBLICA/api/v1/health/ready`. Debe mostrar estado ok,
database ok y migrations ok. Después abrir `http://IP_PUBLICA`.
Registrar usuario, iniciar sesión, crear proyecto, guardar y volver a abrir.
Probar colaboración con dos usuarios, exportación y generación de ZIP.
Si se configuró Gemini, probar una propuesta de texto.

```bash
sudo docker compose -f compose.cloud.yml logs --tail=80 migrate backend web
```

## HTTPS y límites de esta demostración

Con IP y HTTP, la conexión no está cifrada y el navegador no permite grabar
micrófono. Utilizar datos de prueba hasta configurar HTTPS.
Con dominio apuntando a la IP pública, establecer en deploy/.env:
`SITE_ADDRESS=https://DOMINIO` y
`BACKEND_CORS_ORIGINS=["https://DOMINIO"]`.
Ejecutar de nuevo `sudo docker compose -f compose.cloud.yml up -d`.
Caddy obtiene y renueva el certificado automáticamente cuando DNS y puertos
80/443 son accesibles. No instalar Nginx o Certbot a la vez en esos puertos.

La IPv4 pública puede cambiar al detener y volver a iniciar EC2; en ese caso
actualizar ambos valores y DNS si corresponde. Una IP elástica permite fijarla,
pero también consume créditos. El volumen local no sustituye una copia de seguridad.
Antes de terminar la instancia o agotar el plan, respaldar los datos.

## Diferencias corregidas respecto al manual original

- Un solo worker: las salas y reservas colaborativas viven en memoria.
- URL de API y WebSocket basada en la dirección de la web publicada.
- React compilado, sin servidor de desarrollo Vite público.
- Node 22 en la imagen de construcción para el Vite actual.
- Dependencias Python sujetas al requirements.lock existente.
- Migraciones automáticas antes de iniciar API y web.
- Solo el servidor web expone puertos; PostgreSQL y API son internos.
- Las referencias antiguas a 12 meses/30 GiB gratuitos no describen el
  plan actual de esta cuenta basado en créditos.

Referencias: https://caddyserver.com/docs/caddyfile/patterns
y https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-launch-parameters.html
