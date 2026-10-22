# Guía Paso a Paso: Probar el Backend Spring Boot Generado con Postman

Esta guía detalla todo el proceso para poner en marcha y probar de manera local el proyecto backend generado por la plataforma desde tu diagrama UML, comenzando desde la descarga del archivo ZIP hasta la ejecución de peticiones HTTP en Postman.

---

## 1. Prerrequisitos en tu Computadora

Antes de comenzar, asegúrate de tener instaladas las siguientes herramientas en tu sistema operativo:

1. **Java JDK 21**:
   - Verifica en tu terminal:
     ```bash
     java -version
     ```
   - Debe indicar una versión `21.x.x` (por ejemplo, Eclipse Temurin, OpenJDK u Oracle JDK).
2. **Apache Maven (3.8 o superior)**:
   - Verifica en tu terminal:
     ```bash
     mvn -version
     ```
3. **Docker Desktop**:
   - Debe estar instalado y en ejecución en segundo plano para levantar la base de datos PostgreSQL aislada.
4. **Postman**:
   - O cualquier cliente HTTP similar (Thunder Client, Insomnia, cURL).

---

## 2. Paso 1: Descomprimir el Proyecto

1. Localiza el archivo `.zip` descargado desde la plataforma (por ejemplo, `backend-spring.zip` o la solución completa `solucion.zip`).
2. Descomprímelo en una carpeta de tu preferencia (ejemplo: `C:\Proyectos\backend-generado`).
3. **Estructura del proyecto:**
   - Si descargaste **Spring Boot**: En la raíz de la carpeta verás directamente `pom.xml`, `compose.yaml`, `README.md` y la carpeta `src/`.
   - Si descargaste **Solución Completa**: Ingresa a la subcarpeta `backend/`, donde reside el proyecto Spring Boot.

Verifica que existan los archivos clave:
```text
├── compose.yaml                    <- Contenedor Docker para PostgreSQL
├── pom.xml                         <- Configuración de dependencias Maven (Spring Boot 3.5.x)
├── README.md                       <- Documentación específica de tus entidades y rutas
├── mobile-contract.json            <- Contrato de metadatos de la API
└── src/
    ├── main/
    │   ├── java/com/generated/     <- Código fuente (entity, repository, service, api, dto)
    │   └── resources/
    │       └── application.properties
    └── test/
```

---

## 3. Paso 2: Iniciar la Base de Datos con Docker

El proyecto generado incluye su propio archivo `compose.yaml` preconfigurado con PostgreSQL 16. 
> [!IMPORTANT]
> Esta base de datos corre en el puerto **5434** (`localhost:5434`), diseñado intencionalmente para **no colisionar** con el puerto por defecto de PostgreSQL (5432) ni con la base de datos de la plataforma.

Abre una terminal (PowerShell o CMD) dentro de la carpeta del proyecto y ejecuta:

### En PowerShell:
```powershell
# 1. Definir una contraseña local para el usuario 'generated'
$env:DB_PASSWORD = "mipasswordseguro"

# 2. Levantar el contenedor de PostgreSQL
docker compose -p uml-generated up -d
```

### En CMD (Símbolo del sistema):
```cmd
set DB_PASSWORD=mipasswordseguro
docker compose -p uml-generated up -d
```

### En Linux / macOS / Bash:
```bash
export DB_PASSWORD=mipasswordseguro
docker compose -p uml-generated up -d
```

### Verificar que la base de datos esté lista:
Ejecuta:
```bash
docker compose -p uml-generated ps
```
Debe figurar el servicio `db` en estado `Up` exponiendo el puerto `127.0.0.1:5434->5432/tcp`.

---

## 4. Paso 3: Configurar y Ejecutar el Backend

El backend requiere dos variables de entorno principales al ejecutarse en desarrollo:
1. `DB_PASSWORD`: La misma contraseña que le asignaste a Docker (`mipasswordseguro`).
2. `DDL_AUTO`: Por defecto viene en `validate`. Para que Hibernate cree automáticamente las tablas de tu diagrama UML en la base de datos por primera vez, debes indicarle `update`.

En la misma terminal, ejecuta:

### En PowerShell:
```powershell
$env:DB_PASSWORD = "mipasswordseguro"
$env:DDL_AUTO = "update"

# Compilar y arrancar la aplicación
mvn clean spring-boot:run
```

### En CMD:
```cmd
set DB_PASSWORD=mipasswordseguro
set DDL_AUTO=update

mvn clean spring-boot:run
```

### Salida esperada en la terminal:
Cuando la aplicación arranque verás un mensaje similar a:
```text
[INFO] --- spring-boot:run (default-cli) @ uml-backend ---
...
Tomcat started on port 8080 (http) with context path '/'
Started Application in 2.854 seconds (process running for 3.201)
```

¡Tu backend ya está activo y escuchando en `http://localhost:8080`!

---

## 5. Reglas del Contrato REST Generado

Antes de enviar peticiones con Postman, ten en cuenta las reglas de diseño del generador:

1. **Rutas en minúsculas y singular**:
   - Cada clase del diagrama genera su endpoint en minúsculas:
     - Clase `Producto` $\rightarrow$ `/api/producto`
     - Clase `Pedido` $\rightarrow$ `/api/pedido`
     - Clase `DetallePedido` $\rightarrow$ `/api/detallepedido`
2. **Claves Primarias (PK)**:
   - Si el atributo `id` fue asignado automáticamente como Long autoincremental, **NO** se envía en el cuerpo del JSON en `POST` ni en `PUT`.
   - Si tu clase tenía una clave primaria manual explícita (ej. `codigo: String` o `ci: Integer`), sí se envía.
3. **Control de Versión y Concurrencia (`entityVersion`)**:
   - En **POST**: `entityVersion` debe ser `null` o no enviarse.
   - En **PUT**: Es **OBLIGATORIO** enviar el campo `"entityVersion": N` con el valor exacto recibido en el último `GET`. Si no lo envías o envías una versión vieja, el backend responderá `409 Conflict`.
4. **Relaciones en DTOs**:
   - Para evitar ciclos infinitos en JSON, las relaciones foráneas se envían y reciben como IDs:
     - Relación simple (ManyToOne / OneToOne): `"clienteId": 1`
     - Colección (ManyToMany / OneToMany): `"productoIds": [1, 2, 3]`

---

## 6. Paso 4: Pruebas con Postman

Abre Postman y realiza las siguientes pruebas paso a paso:

### Prueba 0: Verificar que la API responde (Comprobación de Salud y Contrato)
- **Método**: `GET`
- **URL**: `http://localhost:8080/api/_meta/contract`
- **Resultado Esperado**: Código `200 OK` con el JSON del contrato y la huella digital (`fingerprint`).

---

### Prueba 1: Listar registros existentes (GET Colección)
- **Método**: `GET`
- **URL**: `http://localhost:8080/api/{entidad}`
  - *Ejemplo*: `http://localhost:8080/api/producto`
- **Parámetros Opcionales (Query Params)**:
  - `page`: `0` (índice de página, por defecto 0)
  - `size`: `20` (elementos por página, máx. 100)
- **Resultado Esperado**: Código `200 OK`. Al inicio devolverá una lista vacía: `[]`.

---

### Prueba 2: Crear un nuevo registro (POST)
- **Método**: `POST`
- **URL**: `http://localhost:8080/api/{entidad}`
  - *Ejemplo*: `http://localhost:8080/api/producto`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body (raw -> JSON)**:
  ```json
  {
    "nombre": "Laptop Gamer",
    "precio": 1250.50,
    "stock": 10
  }
  ```
  *(Reemplaza los campos por los atributos definidos en tu diagrama UML).*
- **Resultado Esperado**:
  - Código: `201 Created`
  - Body de respuesta:
    ```json
    {
      "id": 1,
      "nombre": "Laptop Gamer",
      "precio": 1250.50,
      "stock": 10,
      "entityVersion": 0
    }
    ```
  > [!TIP]
  > Anota el `id` asignado (ej. `1`) y el valor de `entityVersion` (inicia en `0`).

---

### Prueba 3: Consultar el registro por ID (GET Individual)
- **Método**: `GET`
- **URL**: `http://localhost:8080/api/{entidad}/{id}`
  - *Ejemplo*: `http://localhost:8080/api/producto/1`
- **Resultado Esperado**:
  - Código: `200 OK`
  - Body con los datos completos del recurso.

---

### Prueba 4: Actualizar un registro existente (PUT)
- **Método**: `PUT`
- **URL**: `http://localhost:8080/api/{entidad}/{id}`
  - *Ejemplo*: `http://localhost:8080/api/producto/1`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body (raw -> JSON)**:
  ```json
  {
    "nombre": "Laptop Gamer Pro Max",
    "precio": 1400.00,
    "stock": 8,
    "entityVersion": 0
  }
  ```
  *(Nota cómo `"entityVersion": 0` coincide con el valor que tenía el recurso).*
- **Resultado Esperado**:
  - Código: `200 OK`
  - Body con los datos actualizados y el incremento de versión:
    ```json
    {
      "id": 1,
      "nombre": "Laptop Gamer Pro Max",
      "precio": 1400.00,
      "stock": 8,
      "entityVersion": 1
    }
    ```

---

### Prueba 5: Probar una Relación (Entidad Vinculada)
Si tu diagrama tiene una relación, por ejemplo `Pedido` que referencia a un `Cliente`:
1. Crea primero un cliente: `POST /api/cliente` $\rightarrow$ devuelve `id: 1`.
2. Crea el pedido referenciando al cliente:
   - **POST** `/api/pedido`
   - **Body**:
     ```json
     {
       "fecha": "2026-10-14",
       "total": 500.00,
       "clienteId": 1
     }
     ```
3. Consulta la relación desde el pedido:
   - **GET** `http://localhost:8080/api/pedido/1/cliente`
   - Devuelve: `1` (el ID del cliente relacionado).

---

### Prueba 6: Eliminar un registro (DELETE)
- **Método**: `DELETE`
- **URL**: `http://localhost:8080/api/{entidad}/{id}`
  - *Ejemplo*: `http://localhost:8080/api/producto/1`
- **Resultado Esperado**:
  - Código: `204 No Content` (sin contenido en el body).
- **Verificación**: Si vuelves a hacer `GET /api/producto/1`, responderá con `404 Not Found`.

---

## 7. Diagnóstico de Errores Comunes

| Código HTTP | Causa Principal | Solución |
| :--- | :--- | :--- |
| **`400 Bad Request`** | Enviaste `entityVersion` en el `POST` o faltan atributos obligatorios (`@NotNull`). | Quita `entityVersion` al crear registros o llena todos los campos no nulos requeridos. |
| **`404 Not Found`** | El `id` especificado en la URL no existe en la base de datos. | Verifica el ID consultando antes la lista completa con `GET /api/{entidad}`. |
| **`409 Conflict`** | **(A)** Desfase de concurrencia: El `entityVersion` enviado en el `PUT` no coincide.<br>**(B)** Clave primaria manual duplicada.<br>**(C)** Llave foránea inexistente o violación de integridad. | **(A)** Haz un `GET`, copia el `entityVersion` actual y vuelve a enviar el `PUT`.<br>**(B/C)** Asegúrate de que las entidades relacionadas existan previamente. |
| **`Connection Refused`** | La aplicación Spring Boot no puede conectarse a PostgreSQL. | Verifica que Docker esté corriendo (`docker compose -p uml-generated ps`) en el puerto `5434`. |
| **`Password authentication failed`** | La contraseña `DB_PASSWORD` proporcionada a `mvn` no coincide con la del contenedor Docker. | Asegúrate de usar exactamente la misma contraseña en `$env:DB_PASSWORD` tanto al levantar Docker como al ejecutar Maven. |

---

## 8. Detener los Servicios al Finalizar

Cuando termines tus pruebas:
1. En la terminal de Spring Boot: Presiona `Ctrl + C` para detener la aplicación Java.
2. Para apagar el contenedor Docker de la base de datos:
   ```bash
   docker compose -p uml-generated down
   ```
   *(Si deseas borrar también los datos de prueba de la BD, añade `-v`: `docker compose -p uml-generated down -v`).*
