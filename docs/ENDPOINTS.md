# Contrato HTTP observado

## API

Este contrato se deriva del código actual de `api/`; no consta aprobación humana de un contrato acordado. Los ejemplos de respuesta son ilustrativos: los identificadores, las fechas, el contenido del backend y el nombre de la ruta de almacenamiento dependen del estado y la configuración locales.

### Autenticación común

Las cinco rutas requieren el header `Authorization`. El formato que deben enviar los consumidores es `Authorization: Bearer <token>`; el token debe ser emitido por el mecanismo de autenticación acordado. En los ejemplos, `<token emitido para student>` es un marcador, no un valor literal ni un flujo de emisión documentado. La API actual decodifica un token Base64 legacy y construye la identidad a partir de su contenido, pero no verifica una firma criptográfica. La función tampoco valida estrictamente el esquema `Bearer`. La forma de obtener credenciales compatibles y el reemplazo del mecanismo legacy son preguntas abiertas; no se debe tratar este token como autenticación segura.

## GET /api/tasks

1. **Qué hace:** devuelve las tareas asociadas a la identidad autenticada para que el usuario consulte su trabajo.

2. **Autenticación:** requerida. Enviar `Authorization: Bearer <token>`.

3. **Request:** no tiene body. El query `owner` es opcional; si se omite, se usa el username de la identidad.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---|---|
| `owner` (query) | string | No | Propietario solicitado. Si no coincide con el username autenticado, la solicitud se rechaza con `403`. |
| `Authorization` (header) | string | Sí | Credencial requerida por la dependencia de identidad. |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token emitido para student>
Accept: application/json
```

4. **Response exitosa:** `200 OK`, array de tareas. `createdAt` es texto producido por SQLite con formato `YYYY-MM-DD HH:MM:SS`.

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado almacenado; el código no restringe sus valores a un enum. |
| `owner` | string | Username propietario. |
| `priority` | string | Prioridad almacenada; el código no restringe sus valores a un enum. |
| `createdAt` | string | Fecha y hora de creación serializada por SQLite. |

Ejemplo de respuesta con las dos tareas semilla del usuario `student`:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-11-02 10:00:00"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-11-02 10:00:00"
  }
]
```

5. **Respuestas de error posibles:**

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token que no puede decodificarse/validarse con el mecanismo legacy. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | `owner` no coincide con la identidad. | `{"detail":"Not authorized to access this owner"}` |
| `500 Internal Server Error` | Posible fallo no capturado al consultar SQLite u otro error interno. La aplicación no define un cuerpo para este caso; el texto siguiente es el ejemplo del middleware ASGI predeterminado, no un contrato estable. | `Internal Server Error` (texto plano) |

6. **Notas de seguridad:** la consulta limita el propietario al username extraído del token, no a un `owner` arbitrario. Sin embargo, el token no está firmado ni se verifica criptográficamente; la identidad puede ser falsificada mientras siga vigente el mecanismo legacy. No hay autorización por rol en esta ruta. H-API-01 y H-API-02 permanecen pendientes.

## POST /api/tasks

1. **Qué hace:** crea una tarea para que el usuario registre trabajo asociado a su propia identidad.

2. **Autenticación:** requerida. Enviar `Authorization: Bearer <token>`.

3. **Request:** JSON. Todos los campos tienen default y son opcionales; `owner` puede omitirse o ser `null`, en cuyo caso se usa el username autenticado.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---|---|
| `title` (body) | string | No | Título; default `""`. |
| `description` (body) | string | No | Descripción; default `""`. |
| `status` (body) | string | No | Estado; default `"TODO"`. No hay enum declarado. |
| `priority` (body) | string | No | Prioridad; default `"MEDIUM"`. No hay enum declarado. |
| `owner` (body) | string o null | No | Propietario opcional. Si se envía distinto de la identidad, se rechaza con `403`. |
| `Authorization` (header) | string | Sí | Credencial requerida por la dependencia de identidad. |

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token emitido para student>
Content-Type: application/json
Accept: application/json

{"title":"Add tests","description":"Improve coverage","status":"TODO","priority":"HIGH"}
```

4. **Response exitosa:** `201 Created`, tarea creada. El objeto incluye los defaults efectivos y el propietario de la identidad.

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador asignado por SQLite. |
| `title` | string | Título guardado. |
| `description` | string | Descripción guardada. |
| `status` | string | Estado guardado. |
| `owner` | string | Username autenticado. |
| `priority` | string | Prioridad guardada. |
| `createdAt` | string | Fecha y hora de creación, formato SQLite `YYYY-MM-DD HH:MM:SS`. |

Ejemplo de respuesta:

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-11-02 10:00:00"
}
```

5. **Respuestas de error posibles:**

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | El campo `owner` solicita una identidad distinta a la autenticada. | `{"detail":"Not authorized to access this owner"}` |
| `422 Unprocessable Entity` | El JSON no cumple el modelo; por ejemplo, el body no es un objeto. | `{"detail":[{"type":"model_attributes_type","loc":["body"],"msg":"Input should be a valid dictionary or object to extract fields from","input":[]}]}` |
| `500 Internal Server Error` | Posible fallo no capturado al persistir o serializar. La aplicación no define un cuerpo propio; el ejemplo del middleware ASGI predeterminado no es contrato estable. | `Internal Server Error` (texto plano) |

6. **Notas de seguridad:** `owner` nunca debe usarse para asignar tareas a otra identidad; el servicio exige que coincida con el username extraído del token. Esa comprobación no protege frente a falsificación del token legacy. El campo `role` del token no se usa para autorizar esta operación. H-API-01 y H-API-02 siguen pendientes.

## GET /api/summary

1. **Qué hace:** resume el volumen y estado de las tareas del usuario, incluyendo las tareas prioritarias aún abiertas.

2. **Autenticación:** requerida. Enviar `Authorization: Bearer <token>`.

3. **Request:** no tiene body. El query `owner` es opcional y debe corresponder al username autenticado.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---|---|
| `owner` (query) | string | No | Propietario solicitado; por defecto se usa el username autenticado. Otro username causa `403`. |
| `Authorization` (header) | string | Sí | Credencial requerida por la dependencia de identidad. |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token emitido para student>
Accept: application/json
```

4. **Response exitosa:** `200 OK`.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Username cuyo conjunto de tareas se resumió. |
| `total` | integer | Cantidad total de tareas del propietario. |
| `byStatus` | object con valores integer | Conteo de tareas agrupado por cada valor de `status` almacenado. |
| `highPriorityOpen` | integer | Tareas con `priority` `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo con las tareas semilla de `student`:

```json
{"owner":"student","total":2,"byStatus":{"TODO":1,"IN_PROGRESS":1},"highPriorityOpen":1}
```

5. **Respuestas de error posibles:**

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | `owner` no coincide con la identidad. | `{"detail":"Not authorized to access this owner"}` |
| `500 Internal Server Error` | Posible fallo no capturado al consultar SQLite u otro error interno. No hay cuerpo definido por la aplicación; ejemplo predeterminado no garantizado. | `Internal Server Error` (texto plano) |

6. **Notas de seguridad:** la búsqueda se restringe al username extraído del token y no acepta un propietario diferente. El token Base64 carece de firma verificable, por lo que la identidad subyacente no es confiable hasta resolver H-API-01; H-API-02 permanece pendiente. El cálculo considera `DONE` y `ARCHIVED` como estados completados; los demás valores no están restringidos por el modelo.

## POST /api/requirements

1. **Qué hace:** almacena el archivo de requisitos que aporta el usuario para registrar material de su trabajo.

2. **Autenticación:** requerida. Enviar `Authorization: Bearer <token>`.

3. **Request:** multipart/form-data con un archivo en el campo obligatorio `file`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---|---|
| `file` (form-data) | archivo (`UploadFile`) | Sí | Contenido que se guarda bajo el directorio de uploads configurado. No se declaran restricciones de extensión ni tamaño. |
| `Authorization` (header) | string | Sí | Credencial requerida por la dependencia de identidad. |

Ejemplo completo:

```http
POST /api/requirements HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token emitido para student>
Content-Type: multipart/form-data; boundary=ReqFlowBoundary

--ReqFlowBoundary
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
--ReqFlowBoundary--
```

4. **Response exitosa:** `201 Created`.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Username autenticado. |
| `fileName` | string o null | Nombre recibido en la parte multipart. |
| `storedAt` | string | Ruta del archivo guardado, derivada del directorio configurado y el nombre recibido. |
| `size` | integer | Bytes leídos y escritos. |

Ejemplo de respuesta con `uploads` como directorio configurado:

```json
{"owner":"student","fileName":"requirements.txt","storedAt":"uploads/requirements.txt","size":24}
```

5. **Respuestas de error posibles:**

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token"}` |
| `422 Unprocessable Entity` | Falta la parte obligatoria `file`. El cuerpo de error para otras formas multipart malformadas no está caracterizado aquí. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| `500 Internal Server Error` | Posible error no capturado durante lectura/escritura del archivo. La aplicación no define un cuerpo propio; el middleware ASGI predeterminado suele responder texto plano, no garantizado como contrato. | `Internal Server Error` (texto plano) |

6. **Notas de seguridad:** el nombre recibido se concatena directamente al directorio configurado; no se valida la ruta, extensión ni tamaño y el archivo completo se lee antes de escribir. No cargue archivos no confiables ni use esta ruta fuera del entorno aislado hasta corregir H-API-04. La identidad proviene del token legacy no firmado (H-API-01).

## GET /api/backend-health

1. **Qué hace:** consulta el endpoint de salud del backend de autenticación para que un operador vea el estado observado por esta API.

2. **Autenticación:** requerida. Enviar `Authorization: Bearer <token>`.

3. **Request:** no tiene body ni parámetros. La URL consultada se toma de `AUTH_HEALTH_URL`; si no está definida, el código usa `http://localhost:8080/q/health`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---|---|
| `Authorization` (header) | string | Sí | Credencial requerida por la dependencia de identidad. |
| `AUTH_HEALTH_URL` (configuración del servidor) | string URL | No | Destino de la consulta backend; default `http://localhost:8080/q/health`. No es un parámetro enviado por el cliente de esta ruta. |

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token emitido para student>
Accept: application/json
```

4. **Response exitosa:** `200 OK` si la propia ruta completa el procesamiento. El estado HTTP del backend consultado se devuelve en el campo JSON `status`; no se propaga como estado HTTP de esta respuesta.

| campo | tipo | descripción |
|---|---|---|
| `requestedBy` | string | Username extraído de la identidad. |
| `status` | integer | Código HTTP recibido del backend, o `0` cuando falla una de las excepciones capturadas. |
| `body` | string | Bytes de respuesta del backend decodificados como UTF-8, o mensaje genérico si falla una excepción capturada. No se parsea como JSON. |

Ejemplo cuando el backend responde HTTP `503` con el cuerpo `{"status":"DOWN"}`:

```json
{"requestedBy":"student","status":503,"body":"{\"status\":\"DOWN\"}"}
```

Ejemplo cuando falla una excepción capturada de transporte o decodificación:

```json
{"requestedBy":"student","status":0,"body":"Backend health check failed"}
```

5. **Respuestas de error posibles:**

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token"}` |
| `500 Internal Server Error` | Posible excepción no capturada durante el procesamiento. Los errores HTTP/IO y de decodificación UTF-8 sí se capturan y producen `200` con `status: 0`; para otros fallos no hay cuerpo definido por la aplicación. | `Internal Server Error` (texto plano, ejemplo del middleware ASGI predeterminado; no garantizado) |

6. **Notas de seguridad:** la ruta es una consulta saliente a una URL configurada en el servidor; el consumidor no puede elegir el destino mediante query/body. La identidad devuelta es la extraída del token legacy no firmado y no equivale a una identidad verificada. Pregunta abierta: confirmar con el despliegue qué valores de `AUTH_HEALTH_URL` se permiten y cómo se controla esa configuración.

## Preguntas abiertas

- ¿Qué emisor entrega el token, cómo se obtiene y cuál será el contrato firmado que sustituya el token Base64 legacy? H-API-01 y H-API-02 continúan pendientes.
- ¿Qué estados y prioridades son válidos para negocio? El modelo actual acepta strings sin enum.
- ¿Qué extensiones y tamaño máximo deben permitirse en `POST /api/requirements`? H-API-04 continúa pendiente.
- ¿Qué formato de error interno debe considerarse contrato en cada entorno? La aplicación no define actualmente esos cuerpos y el middleware/proxy puede modificarlos.
- ¿Qué estado y cuerpo produce el parser ante un multipart malformado distinto de omitir `file`? No está caracterizado por las pruebas actuales.
- ¿Qué URLs se autorizan para `AUTH_HEALTH_URL` en cada despliegue?

## Referencias de implementación

- Rutas, métodos, parámetros y status de éxito: `api/app/routes.py`.
- Tipos y aliases de request/response: `api/app/schemas.py`.
- Autenticación y errores `401`: `api/app/security.py`.
- Reglas de propietario, resumen, carga y backend health: `api/app/services.py`.
- Esquema, datos iniciales y persistencia de tareas: `api/app/repositories.py`.
- Casos de contrato ejercitados por la suite: `api/tests/test_api.py`.