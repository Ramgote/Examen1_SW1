# Plataforma colaborativa UML 2.5

Sprint 10: generación conjunta Spring Boot + Flutter Android desde una misma
versión guardada del canvas. Incluye modelos y servicios Dart, contrato compartido,
validación y descarga ZIP desde la web. Aceptación manual de la nueva descarga pendiente.
[Implementación, finalidad y pruebas](docs/sprint-10.md).

Sprint 9: conversación visible y CRUD móvil por texto, con datos faltantes,
relaciones, control de versión y confirmación de borrado. Pruebas automatizadas
y recorrido contra Spring real aprobados; el usuario confirmó la prueba en teléfono.
[Implementación, finalidad y ensayo](docs/sprint-9.md).

Sprint 8: contrato compartido Spring/móvil, endpoint de compatibilidad, URL
persistida y errores de conexión explícitos implementados. Pruebas locales
aprobadas; el usuario confirmó conexión al backend y error por puerto incorrecto en teléfono.
[Implementación, finalidad y prueba LAN](docs/sprint-8.md).

Plan móvil del 21/09/2026: [implementación y cierre de Flutter](docs/plan-implementacion-mobile.md).
Define los sprints 8–12 para contrato común, CRUD conversacional, generación
conjunta Spring/Flutter, voz local y aceptación en teléfono. Estado: planificado.

Ensayo web al 20/09/2026: el usuario aprobó colaboración, persistencia visual,
IA multimodal e intercambio mutuo con EA 17. El Spring Cliente–Pedido pasó
compilación, arranque y 17 comprobaciones HTTP; el usuario también aprobó el
ensayo manual con REST Client. Las cinco filas del ensayo de presentación web
quedan aprobadas. [Guía del ensayo Spring](docs/ensayo-spring-cliente-pedido.md).

Plataforma universitaria de diseño UML con React, FastAPI y PostgreSQL. El generador
Spring Boot está implementado en el sprint 5 y el asistente multimodal Gemini en el
sprint 6 (texto, imagen y voz validados; aceptación manual confirmada). Flutter corresponde a una fase posterior. El editor UML,
la colaboración en tiempo real y el intercambio XMI del perfil de clases ya están implementados.

Requerimientos comprendidos, límites, decisiones por revisar y estimación de avance
(17/09/2026): [docs/requerimientos-y-alcance.md](docs/requerimientos-y-alcance.md).
Avance orientativo del alcance original: **aproximadamente 56%**, según la ponderación
documentada; no equivale a contar sprints ni a una aceptación final del producto.

## Sprint 0: base ejecutable

**Completado y verificado en Docker:** PostgreSQL y API saludables, migración
terminada correctamente, esquema validado con Alembic y frontend accesible.

Implementación y explicación para la defensa: [docs/sprint-0.md](docs/sprint-0.md).

## Sprint 1: usuarios y proyectos

Implementado: registro, login, identidad actual, proyectos y colaboradores con permisos
de propietario, editor y lector. La API fue verificada con PostgreSQL y HTTP real en
Docker. React compila y pasa ESLint; queda pendiente la revisión visual interactiva.

Pasos, finalidad, contratos, pruebas y guion de defensa:
[docs/sprint-1.md](docs/sprint-1.md).

## Sprint 2: editor UML

Desde un proyecto, pulse **Abrir diagrama UML**. Puede crear y mover clases, editar
atributos y métodos y conectar relaciones. El lector solo consulta. Desde el
sprint 3, los cambios se guardan y comparten automáticamente; los cambios
incompatibles conservan el borrador local para descargarlo antes de recargar.

Implementación, reglas, pruebas y guion de defensa:
[docs/sprint-2.md](docs/sprint-2.md).

## Sprint 3: colaboración en tiempo real

Salas WebSocket autenticadas, presencia, sincronización automática, combinación
de cambios compatibles, detección de conflictos y reconexión con borrador local.
La versión de Docker utiliza un solo proceso de backend. Los cambios de permisos
se comprueban durante la sesión. No se requieren migraciones nuevas.

Pruebas de PostgreSQL, cliente y WebSockets reales verificadas. En el sprint 7,
el autor confirmó el bloqueo y la liberación de clases con dos usuarios.
Pasos, finalidad y guion para la defensa:
[docs/sprint-3.md](docs/sprint-3.md).

## Sprint 4: intercambio UML/XMI

Implementado: exportación del modelo guardado a XMI 2.5.1, importación con vista
previa, validación y avisos de compatibilidad, y reemplazo confirmado con control
de versión. La importación aplicada se comparte con los colaboradores conectados.
Desde el editor abra **Intercambio XMI · importar y exportar**.
El importador separa los IDs del modelo de los metadatos de extensiones; los
duplicados reales se informan con sus líneas XML para facilitar su revisión.
Se verificó el archivo real `DC_Tienda.xml` de EA 15.0.1514: se resuelven su
catálogo de primitivos Java, los retornos void y las referencias de asociaciones.
El editor muestra todos los tipos disponibles en selectores de atributos,
parámetros y retornos; `void` se ofrece únicamente para el retorno de métodos.
Desde el sprint 7, la exportación ofrece **Enterprise Architect 17.0 · XMI 2.1 con diagrama de clases**: paquete único
con todo el modelo y extensión gráfica, además de la opción XMI estándar.
La estructura está probada; su representación final dentro de EA sigue pendiente
de aceptación visual.

Verificado con pruebas de PostgreSQL, HTTP y WebSockets en Docker, pruebas del
cliente, compilación y ESLint. Pendientes la revisión visual y el intercambio
de la exportación en una instalación de Enterprise Architect; se soporta un perfil
documentado, no todos los dialectos ni los diagramas propietarios de EA.

Pasos, finalidad, límites, archivo de ejemplo y guion de defensa:
[docs/sprint-4.md](docs/sprint-4.md).

## Sprint 5: generación Spring Boot

Desde el editor abra **Generar backend Spring Boot**, valide el modelo guardado,
revise los avisos y descargue el ZIP. Incluye Java 21, Maven, entidades JPA,
repositorios, DTO, servicios CRUD, controladores REST y configuración PostgreSQL.
La descarga respeta permisos y versión; no modifica el lienzo ni copia secretos.

Se explicitan las reglas de claves, relaciones y herencia y se rechazan modelos
que el perfil aún no transforma. El código generado es una base ejecutable; su
autenticación de dominio, migraciones productivas y reglas de negocio requieren
trabajo adicional. Implementación por paso, finalidad, uso y pruebas:
[docs/sprint-5.md](docs/sprint-5.md).

Verificado: 48 pruebas del backend con PostgreSQL en Docker, 12 del frontend,
ESLint/build y cuatro pruebas Java del proyecto generado. El JAR compilado también
pasó un recorrido CRUD y relacional por HTTP real. Pendiente la aceptación visual.

## Sprint 6: asistente IA multimodal

En el editor abra **Asistente IA · texto, imágenes y voz**. Permite combinar una
instrucción escrita, hasta tres imágenes y un audio adjunto o grabado. Gemini
devuelve una propuesta validada con comparación antes/después; aplicar requiere
confirmación, permiso de edición y la misma versión del lienzo.
Al recibir una propuesta o error, el panel abre y enfoca el resultado. Generar una
propuesta no cambia el canvas: pulse **Aplicar cambios al diagrama** para guardarla.

Configure `GEMINI_API_KEY` en `backend/.env` y recree el contenedor backend para
cargarla. La clave permanece en el servidor. Modelo predeterminado:
`GEMINI_MODEL=gemini-3.6-flash`. Sin clave se informa configuración pendiente;
no se sustituyen respuestas reales por simulaciones.

Verificado: 60 pruebas del backend con PostgreSQL, 14 del frontend, ESLint y build.
La integración se probó con respuestas controladas y una propuesta UML real de texto.
Se corrigió el esquema de Function Calling y el modelo no disponible para cuentas nuevas.
Pendientes imagen/audio reales y la prueba visual/micrófono. Este módulo usa IA en
la nube; el control de voz local de Flutter se implementará por separado.

Pasos, finalidad, configuración y casos de aceptación: [docs/sprint-6.md](docs/sprint-6.md).

Revisión de `exports/DC1.png`: diagnóstico de campos UML, un reintento de corrección
y reglas de transcripción de nombres/multiplicidades. Las 15 pruebas del asistente
pasaron con PostgreSQL. Gemini respondió 503 por alta demanda durante las pruebas
reales de esa imagen; ahora se informa ese fallo por separado. Su aceptación visual
permanece pendiente y no se modifican diagramas ante errores.

## Sprint 7: reservas de clases y colaboración

Seleccionar una clase solicita una reserva exclusiva por conexión. Se muestra quién
la edita; los demás no pueden modificarla ni cambiar relaciones que la afecten.
**Guardar y terminar edición** guarda y libera; **Recargar guardado** descarta el
borrador no sincronizado y libera. El autoguardado mantiene la reserva hasta terminar.
Las reservas caducan tras 45 segundos sin renovación y se verifican también al
aplicar IA o XMI. La implementación requiere un único proceso backend.

EA 17.0 es el destino predeterminado de exportación, conservando EA 15 y XMI estándar.
Se importan posiciones del primer diagrama de clases de EA. Verificados: 66 pruebas
backend con PostgreSQL, 17 del cliente, ESLint/build y dos WebSockets reales.
El autor confirmó manualmente que, con dos usuarios, la clase permanece bloqueada
hasta pulsar **Guardar y terminar edición**. El intercambio real dentro de EA 17.0
y los escenarios manuales de colaboración, persistencia e IA fueron aceptados
el 20/09/2026; véase el registro de correcciones.

Pasos, finalidad, uso y criterios de aceptación: [docs/sprint-7.md](docs/sprint-7.md).

## Sprint 8: contrato compartido y cliente móvil

Se definió el descriptor `mobile-contract.json` determinista con huella SHA-256 generado desde el plan de persistencia y expuesto mediante `GET /api/_meta/contract` en Spring Boot. La app móvil Flutter valida la huella antes de operar.
Documentación: [docs/sprint-8.md](docs/sprint-8.md).

## Sprint 9: asistente conversacional por texto

Implementación del motor de diálogo determinista (`dialogue_service.dart`) basado en el contrato. Soporta flujos multiturno con solicitud de campos obligatorios faltantes, cancelación, resolución de relaciones, paginación completa y control de concurrencia optimista (HTTP 409).
Documentación: [docs/sprint-9.md](docs/sprint-9.md).

## Sprint 10: generación conjunta Spring Boot + Flutter

Generación dual desde la interfaz web (`POST /api/v1/projects/{id}/generate/solution`). Descarga un único ZIP con el backend Java Maven y la aplicación Flutter Android preconfigurada con los DTOs y servicios del modelo UML.
Documentación: [docs/sprint-10.md](docs/sprint-10.md).

## Sprint 11: voz y NLU locales en Android

Integración de reconocimiento de voz nativo en Android (STT) y síntesis de voz (TTS) en español, con protección contra auto-escucha, conmutador de sonido y pruebas unitarias de voz. Aceptado y verificado en dispositivo físico real.
Documentación: [docs/sprint-11.md](docs/sprint-11.md).

## Sprint 12: ensayo integrado y cierre del módulo móvil

Generación y validación limpia de dos dominios completos (*Cliente-Pedido* y *Taller*), verificación de 90 pruebas backend y 22 pruebas Flutter, y cierre de la matriz de aceptación de extremo a extremo.
Documentación: [docs/sprint-12.md](docs/sprint-12.md).

## Ejecución de la plataforma

Para abrir el editor web desde un móvil en la misma Wi-Fi, usar la configuración
opcional `docker-compose.lan.yml`. Pasos, URL y diagnóstico:
[pruebas desde el móvil](docs/pruebas-movil-red-local.md). Esto no es la app Flutter.
### Desarrollo local en Windows

Requisitos: Python 3.14, Node.js 20.19 o superior compatible con Vite, PostgreSQL
en ejecución y una base `uml_platform_db`. El entorno existente usa Python 3.14.3.
Ejecute desde la raíz del proyecto:

```powershell
py -3.14 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt -c backend/requirements.lock
backend/.venv/Scripts/python.exe backend/scripts/init_env.py
```

Si el entorno virtual ya existe, omita su creación. El script conserva cualquier `.env`
existente; si crea uno nuevo, genera secretos aleatorios. Configure en `backend/.env`
el usuario, contraseña, puerto y nombre de su PostgreSQL local. No envíe contraseñas
por chat ni las incluya en Git. Si la base no existe, créela con pgAdmin antes de migrar.

En una terminal:

```powershell
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

En otra terminal, desde la raíz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

`npm.cmd` evita depender de la política de ejecución de scripts PowerShell.
La interfaz muestra registro e inicio de sesión y, después del acceso, proyectos,
colaboradores y el editor UML. La sesión se mantiene en memoria; al recargar hay
que iniciar sesión otra vez. Guarde el diagrama antes de cerrar o recargar.

### Direcciones de comprobación

| Dirección | Resultado esperado |
| --- | --- |
| http://127.0.0.1:5173 | Aplicación React |
| http://127.0.0.1:8000/docs | Contrato OpenAPI interactivo |
| http://127.0.0.1:8000/api/v1/health/live | HTTP 200: proceso disponible |
| http://127.0.0.1:8000/api/v1/health/ready | HTTP 200: PostgreSQL y revisión Alembic disponibles |

`ready` devuelve HTTP 503 si falla la conexión, falta la tabla de Alembic o la revisión
no coincide. Comprueba la revisión registrada, no audita toda la estructura SQL.
Para comparar los modelos con la base ejecute `python -m alembic check` desde backend.

### Alternativa Docker

Prepare primero `backend/.env` con el script anterior. Con Docker Desktop en ejecución:

```powershell
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up -d --build
docker compose --env-file backend/.env ps -a
```

Secuencia: PostgreSQL saludable → migración terminada → API saludable → frontend.
Dentro de Docker se usa `db:5432`; desde Windows se usa el puerto publicado.
Si PostgreSQL local ocupa 5432, para esta alternativa configure otro `POSTGRES_PORT`
en `.env`, por ejemplo 5433. No ejecute simultáneamente ambas alternativas con los mismos puertos.

Las credenciales de un volumen PostgreSQL existente no cambian por editar `.env`.
Conserve las credenciales originales o cambie la contraseña mediante PostgreSQL.
`docker compose --env-file backend/.env down` detiene la alternativa Docker y conserva
el volumen. No use `down -v` para reiniciar una instalación con datos que quiera conservar.

Compose prepara desarrollo local, no un despliegue de producción. La imagen usa
PostgreSQL 16; la instalación local encontrada es PostgreSQL 17. Las imágenes base
mantienen tags de versión mayor y no están fijadas por digest.

### Correcciones de interfaz — 19/09/2026

Se verificaron los puertos originales de `.env` sin modificarlos. El asistente
permanece visible durante sus solicitudes y conserva su contenido al ocultarlo;
se retiraron los controles de minimizar/maximizar del encabezado y la minimización
del asistente. Detalle y validación en
[Correcciones de UI: primera entrega](docs/correcciones-ui-2026-09-19.md).

Se añadieron confirmación antes de descartar cambios, descarga del borrador JSON
y un indicador que distingue guardado confirmado, cambios pendientes, sincronización
y errores. Validación: 22 pruebas aprobadas y compilación correcta. Detalle en
[Correcciones de UI: prioridades 1 y 2](docs/correcciones-ui-2026-09-19.md).

Las prioridades 3, 4 y 5 incorporan persistencia de tamaños/conectores/vista,
autoorganización con reservas y tipos UML explícitos (interfaz y enumeración) en
editor, PostgreSQL y XMI. El perfil Spring CRUD rechaza explícitamente esos tipos
hasta ampliar su generación Java. Todas las entregas y pruebas se consolidan en
[el registro de correcciones de UI](docs/correcciones-ui-2026-09-19.md).

Seleccionar elementos ya no los reserva: el inspector permite consultar y ofrece
“Editar y mover” / “Editar relación” para iniciar explícitamente la edición.
El registro incluye también las instrucciones de reinicio manual de los servicios.

Ensayo manual PC/móvil confirmado por el usuario el 20/09/2026: edición exclusiva,
guardado, liberación y recuperación de conexión/modelo tras desconectar y reconectar
la Wi-Fi. La fila de colaboración del ensayo de presentación queda completada.

El usuario confirmó también la persistencia visual de tamaños, posiciones y
conectores al guardar, salir y reabrir el proyecto (20/09/2026).

IA desde la interfaz validada manualmente por el usuario el 20/09/2026: imagen y
micrófono reales, propuesta visible y aplicación correcta al canvas.

Exportación EA corregida el 20/09/2026: una importación real en un repositorio
temporal de EA creó el diagrama Prueba2 con 7 clases y 8 conectores. El archivo
anterior no creaba ningún diagrama. La aceptación posterior del usuario confirma
el intercambio mutuo del ejemplo Cliente–Pedido;
archivo de prueba: `exports/Prueba2-ea17-diagrama-corregido.xmi`.

Prioridades 6 y 7: XMI conserva realización, clase de asociación y vinculación
de plantilla dentro del perfil documentado; el inspector permite declarar parámetros
y sustituciones. Los casos no representables se rechazan expresamente. Lint queda
sin errores; 26 pruebas frontend y las nuevas pruebas de intercambio pasan.
La validación visual de importación y exportación mutuas con EA 17 fue confirmada
por el usuario el 20/09/2026 tras las correcciones. Detalles en el mismo registro.

Si se cambia `GEMINI_API_KEY` o `GEMINI_MODEL` en `backend/.env`, usar
`docker compose up -d --no-deps --force-recreate backend`: un `restart` conserva
las variables anteriores del contenedor. El registro de correcciones documenta
el diagnóstico sin exposición de claves y la prueba satisfactoria con `DC1.png`.

### Pruebas

```powershell
cd backend
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m alembic check
```

Las pruebas unitarias usan conexiones simuladas: no requieren PostgreSQL ni modifican datos.
`alembic check` sí requiere la base real. En frontend ejecute `npm.cmd run build`
y `npm.cmd run lint`.

`requirements.lock` conserva las versiones instaladas usadas en la verificación local;
se aplica como archivo de restricciones a pip. El build y arranque Linux de Docker
también se verificaron al cerrar el sprint 0. `npm ci` instala las versiones del
`package-lock.json`.



### Correcci?n de intercambio EA 17 ? 20/09/2026

El importador acepta la multiplicidad ilimitada que EA representa con l?mites
`-1/-1`. El exportador declara las propiedades UML de atributos escalares para
impedir `{bag}`, manteniendo independiente la unicidad de base de datos.
Se actualiz? `exports/cliente-pedido-ea17.xmi` y se verific? su importaci?n en un
repositorio temporal de EA. Diagn?stico y pruebas en
[el registro de correcciones](docs/correcciones-ui-2026-09-19.md).
