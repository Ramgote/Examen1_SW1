# Guía Portátil de Defensa: Puesta en Marcha del Backend Generado

Esta guía está diseñada como un resumen rápido y portátil para tu demostración y defensa. Incluye los comandos para **PowerShell** y **CMD**, el orden de pruebas en Postman y soluciones rápidas a errores frecuentes.

---

## 1. Reglas de Oro (Antes de Ejecutar)

1. **Ubicación correcta:** Al descomprimir la solución completa, **siempre** debes entrar a la subcarpeta `backend/` (donde están `pom.xml` y `compose.yaml`).
2. **Limpieza de Base de Datos:** Para evitar conflictos de tablas o columnas de intentos previos, **siempre** arranca con `down -v`.
3. **Variables de Entorno:** Debes definir `DB_PASSWORD` y `DDL_AUTO=update` en la misma terminal donde compiles.
4. **Orden en Postman:** Primero se crean las entidades independientes (ej. `Cliente`, `Producto`), luego las dependientes con claves foráneas (ej. `Venta`).
5. **Control de Versión (`entityVersion`):**
   - En **POST**: **NO** envíes `entityVersion`.
   - En **PUT**: **SÍ** debes enviar `"entityVersion": N` con el número devuelto por el último `GET`.

---

## 2. Puesta en Marcha: CMD (Símbolo del Sistema)

Abre **CMD** en la carpeta donde descomprimiste el proyecto y ejecuta:

### Paso 1: Entrar al backend
```cmd
cd backend
```

### Paso 2: Limpiar y levantar PostgreSQL en Docker
```cmd
docker compose -p uml-generated down -v
set DB_PASSWORD=mipasswordseguro
docker compose -p uml-generated up -d
```
> [!WARNING]
> En CMD **no dejes espacios** alrededor del `=`:
> - Correcto: `set DB_PASSWORD=mipasswordseguro`
> - Incorrecto: `set DB_PASSWORD = mipasswordseguro`

### Paso 3: Arrancar Spring Boot con Maven
```cmd
set DDL_AUTO=update
mvn spring-boot:run
```

---

## 3. Puesta en Marcha: PowerShell

Abre **PowerShell** en la carpeta donde descomprimiste el proyecto y ejecuta:

### Paso 1: Entrar al backend
```powershell
cd backend
```

### Paso 2: Limpiar y levantar PostgreSQL en Docker
```powershell
docker compose -p uml-generated down -v
$env:DB_PASSWORD = "mipasswordseguro"
docker compose -p uml-generated up -d
```

### Paso 3: Arrancar Spring Boot con Maven
```powershell
$env:DDL_AUTO = "update"
mvn spring-boot:run
```

---

## 4. Atajos en Una Sola Línea (Arranque Automático)

Si quieres ejecutar todo el arranque del tirón sin escribir comando por comando:

### En CMD:
```cmd
cd backend && docker compose -p uml-generated down -v && set DB_PASSWORD=mipasswordseguro && docker compose -p uml-generated up -d && set DDL_AUTO=update && mvn spring-boot:run
```

### En PowerShell:
```powershell
cd backend; docker compose -p uml-generated down -v; $env:DB_PASSWORD="mipasswordseguro"; docker compose -p uml-generated up -d; $env:DDL_AUTO="update"; mvn spring-boot:run
```

*(Espera unos segundos hasta ver `Tomcat started on port 8080`)*.

---

## 5. Tabla de Equivalencias entre Terminales

| Acción 						| PowerShell 								| CMD (Símbolo del sistema) |
| :--- 							| :--- 										| :--- |
| **Definir clave de BD** 		| `$env:DB_PASSWORD = "mipasswordseguro"` 	| `set DB_PASSWORD=mipasswordseguro` |
| **Definir modo DDL** 			| `$env:DDL_AUTO = "update"` 				| `set DDL_AUTO=update` |
| **Ver valor de variable** 	| `echo $env:DB_PASSWORD` 					| `echo %DB_PASSWORD%` |
| **Listar archivos** 			| `ls` o `dir` 								| `dir` |
| **Encadenar comandos** 		| `;` 										| `&&` |
| **Comandos Docker / Maven** 	| Idénticos (`docker compose`, `mvn`) 		| Idénticos (`docker compose`, `mvn`) |

---

## 6. Flujo de Demostración en Postman

> **Header obligatorio en POST y PUT:**  
> `Content-Type: application/json`

### 1. Comprobación del Contrato
- **GET** `http://localhost:8080/api/_meta/contract`
- *Explicación:* Muestra el contrato JSON oficial con la huella digital SHA-256 de sincronización con la app móvil.

### 2. Crear Entidades Maestras (POST)
- **POST** `http://localhost:8080/api/cliente`
  ```json
  {
    "nombre": "Carlos Perez"
  }
  ```
  *(Devuelve `id: 1`)*.

- **POST** `http://localhost:8080/api/producto`
  ```json
  {
    "codigo": "P01",
    "nombre": "Laptop Gamer"
  }
  ```
  *(Devuelve `id: 1`)*.

### 3. Crear Entidad con Relaciones (POST)
- **POST** `http://localhost:8080/api/venta`
  ```json
  {
    "fecha": "2026-10-15",
    "total": 1200.0,
    "clienteRel70e28c70Id": 1,
    "productoRelbc222dd2Ids": [1]
  }
  ```
  *(Demuestra que las relaciones se vinculan por IDs sin ciclos infinitos).*

### 4. Consultar Sub-recursos Relacionales (GET)
- `GET http://localhost:8080/api/venta/1/clienteRel70e28c70` $\rightarrow$ Devuelve `1` (ID del cliente).
- `GET http://localhost:8080/api/venta/1/productoRelbc222dd2` $\rightarrow$ Devuelve `[1]` (IDs de productos).

### 5. Demostrar Bloqueo Optimista de Concurrencia (PUT)
- **PUT** `http://localhost:8080/api/cliente/1`
  ```json
  {
    "nombre": "Carlos Perez Actualizado",
    "entityVersion": 0
  }
  ```
  *(Responde `200 OK` e incrementa a `"entityVersion": 1`)*.
- **Vuelve a enviar exactamente el mismo JSON con `entityVersion: 0`:**
  *(Responde inmediatamente con `409 Conflict`, demostrando protección ante sobreescrituras concurrentes)*.

---

## 7. Chuleta de Emergencia (Solución en 5 segundos)

| Error en la terminal / Postman 				| Causa 												| Solución Inmediata |
| :--- 											| :--- 													| :--- |
| `No plugin found for prefix 'spring-boot'` 	| Estás en la raíz del proyecto. 						| Escribe: `cd backend` |
| `column ... does not exist` 					| La BD conservó tablas viejas. 						| Ejecuta: `docker compose -p uml-generated down -v` y vuelve a iniciar. |
| `Unrecognized field "..."` 					| El nombre del campo en Postman no coincide con el Java Request. | Abre `mobile-contract.json` y verifica los nombres exactos de los campos. |
| `400: No envíe entityVersion al crear` 		| Enviaste `entityVersion` en el POST. 					| Elimina `"entityVersion"` del body en Postman (solo se envía en el PUT). |
| `Connection refused` 							| Docker no está corriendo o PostgreSQL está apagado. 	| Verifica que Docker Desktop esté en verde y levanta el contenedor con `docker compose -p uml-generated up -d`. |
