# Hallazgos

## API

Matriz iniciada mediante discovery estático y actualizada con cambios y verificaciones reales hasta el 2026-11-03. El estado y las evidencias de cada hallazgo se mantienen por fila; los advisories SCA se reportan según los resultados del scanner.

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido y sin firma | Vulnerabilidad | El servidor decodifica el contenido y compara un secreto constante que también forma parte del token, pero no verifica una firma criptográfica. Un cliente puede construir credenciales con otro usuario o rol y una expiración futura. | `api/app/security.py:10,14-24` | alta | Pendiente |
| H-API-02 | api | Autorización de tareas controlada por el cliente | Vulnerabilidad | `owner` en las consultas permite leer tareas de otra identidad; al crear, el payload también puede asignar cualquier propietario. La identidad del token no limita esas operaciones. | `api/app/services.py:30-38,100-102`; `api/app/security.py:10,14-24`; `api/tests/test_api.py:82-100` | alta | Pendiente: los overrides distintos reciben 403, pero el username proviene de un token Base64 forjable; cerrar tras H-API-01 y probar identidad firmada. |
| H-API-03 | api | Consultas SQL construidas por concatenación | Vulnerabilidad | Valores de `owner`, título, descripción, estado y prioridad se interpolan en SQL. Entradas manipuladas pueden alterar las consultas de lectura o inserción. | `api/app/repositories.py:40-54`; `api/tests/test_api.py:57-68` | alta | Resuelto: filtros, inserciones y lectura por ID usan parámetros; la prueba con comillas pasa. |
| H-API-04 | api | Carga de archivos usa el nombre recibido sin límites | Vulnerabilidad | El nombre se une directamente al directorio de uploads y el contenido completo se lee antes de guardarse; no se observa validación de ruta/extensión ni límite de tamaño. Puede permitir escritura fuera del directorio previsto o agotar almacenamiento/memoria. | `api/app/services.py:57-65` | alta | Pendiente |
| H-API-05 | api | Dependencias fijadas pendientes de análisis SCA | Vulnerabilidad | `urllib3` y `python-multipart` están fijadas a las versiones indicadas por el RETO. Esto confirma los objetivos de revisión, pero no demuestra por sí solo un CVE aplicable; falta registrar el análisis de advisories y la decisión de remediación. | `api/requirements.txt:1,4-6` | media | Resuelto: actualizadas FastAPI, Starlette, urllib3 y python-multipart a pins compatibles; pip-audit no reportó vulnerabilidades conocidas. |
| H-API-06 | api | Rutas, persistencia, reglas y serialización concentradas en un módulo | Refactor | `main.py` crea directorios y conexión, crea/es inicializa tablas, define serialización y declara endpoints con SQL y lógica de negocio. El acoplamiento dificulta probar y cambiar cada responsabilidad por separado. | `api/app/main.py:1-38`; `api/app/routes.py:1-51`; `api/app/repositories.py:1-58`; `api/app/services.py:1-102`; `api/app/schemas.py:1-50`; `api/app/security.py:1-24` | media | Resuelto: composición, rutas, persistencia, servicios, esquemas y autenticación están separados; suite API: 13 passed. |
| H-API-07 | api | Tipado y manejo de errores/calidad inconsistentes | Refactor | El body de creación usa `dict[str, Any]`, hay capturas amplias de `Exception` y lógica condicional anidada en el resumen; la consulta de columnas de tareas se repite. Esto reduce validación, claridad y diagnóstico seguro; además, el error de autenticación se concatena en la respuesta HTTP. | `api/app/schemas.py:1-50`; `api/app/security.py:22-24`; `api/app/services.py:40-56,79-102`; `api/tests/test_api.py:72-80,122-139,172-184` | media | Resuelto: requests/responses tipados, validación 422, errores genéricos y resumen simplificado con pruebas. |
| H-API-08 | api | Conexión SQLite compartida sin serialización explícita | Robustez | `create_app` crea una conexión y la comparte mediante un único repositorio entre rutas síncronas; se permite su uso desde varios hilos, pero no se observa un mecanismo que serialice las operaciones. Bajo concurrencia podrían intercalarse operaciones/transacciones o fallar solicitudes. | `api/app/main.py:19,38-40`; `api/app/routes.py:19-35`; `api/app/repositories.py:9-12,43-53` | media | CANDIDATO |
| H-API-09 | api | Estado y prioridad de tareas aceptan valores sin dominio validado | Contrato | El request limita `status` a `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED` y `priority` a `LOW`, `MEDIUM`, `HIGH`, con coincidencia exacta y rechazo `422`. Los valores legacy siguen disponibles en lectura y resumen. | `api/app/schemas.py:15-32`; `api/app/services.py:24,50`; `api/app/repositories.py:43-55`; `api/tests/test_api.py:95-176` | media | Resuelto: suite API 52 passed, cobertura 100%. |
| H-API-10 | api | Campos de texto de tarea sin límite de longitud | Robustez | `title` y `description` no declaran longitud máxima y se guardan directamente. Solicitudes autenticadas repetidas con valores grandes pueden aumentar almacenamiento y memoria consumida al listar/responder tareas. | `api/app/schemas.py:13-15`; `api/app/repositories.py:43-53` | media | CANDIDATO |
| H-API-11 | api | Health check devuelve HTTP 200 aunque falle el backend | Contrato | Ante una respuesta upstream `503` o un error de conexión, el servicio devuelve el estado dentro del JSON (o `0`) sin cambiar el status HTTP de la ruta; una sonda que solo revise HTTP puede interpretar la dependencia caída como saludable. | `api/app/routes.py:46-50`; `api/app/services.py:68-86`; `api/tests/test_api.py:291-331` | media | CANDIDATO |

## Seguimiento de hallazgos API

### H-API-08 — Conexión SQLite compartida sin serialización explícita
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:19,38-40` crea una conexión por aplicación y la entrega al repositorio compartido; `api/app/repositories.py:9-12` usa `check_same_thread=False`; las rutas síncronas `api/app/routes.py:19-35` usan ese repositorio.
- Impacto: si llegan operaciones concurrentes, varias solicitudes pueden acceder a la misma conexión sin una exclusión visible; se debe comprobar si hay intercalado de transacciones, errores o resultados inconsistentes.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: persistencia y resultados de `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary`.
- Cómo validarlo: agregar una prueba de concurrencia que envíe creaciones y lecturas simultáneas, compruebe estados HTTP y errores, y verifique que cada creación aparece exactamente una vez en los listados y agregados.

### H-API-09 — Estado y prioridad de tareas aceptan valores sin dominio validado
- Estado: Resuelto
- Evidencia: `api/app/schemas.py:15-32` declara los catálogos; `api/app/services.py:24,50` usa los enums para clasificación; `api/app/repositories.py:43-55` persiste strings y mantiene lecturas legacy.
- Impacto: valores nuevos fuera del catálogo exacto se rechazan con `422`; los registros existentes siguen apareciendo sin alteración en listados y conteos.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: request/response de `POST /api/tasks` y agregados `byStatus`/`highPriorityOpen` de `GET /api/summary`.
- Cómo validarlo: pruebas dirigidas de catálogos, valores inválidos, estados cerrados y legacy: **22 passed**; `python tools/lab.py test api`: **52 passed**, cobertura total **100%**.

### H-API-10 — Campos de texto de tarea sin límite de longitud
- Estado: CANDIDATO
- Evidencia: `api/app/schemas.py:13-15` no fija límites a `title` ni `description`; `api/app/repositories.py:43-53` persiste ambos campos y los vuelve a leer.
- Impacto: una identidad autorizada podría almacenar valores arbitrariamente grandes; solicitudes repetidas pueden aumentar el tamaño de SQLite y el uso de memoria/respuesta al consultar tareas. No se encontró un límite contractual que permita proponer un umbral concreto.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: request y response de `POST /api/tasks`, además de respuestas de `GET /api/tasks`.
- Cómo validarlo: acordar máximos con producto, probar longitud en el límite y por encima, y verificar rechazo explícito sin persistencia de valores excesivos.

### H-API-11 — Health check devuelve HTTP 200 aunque falle el backend
- Estado: CANDIDATO
- Evidencia: `api/app/services.py:71-86` conserva el estado upstream en el cuerpo o devuelve `status=0`; `api/tests/test_api.py:291-331` verifica HTTP 200 para una respuesta upstream `503` y para una falla capturada. La ruta `api/app/routes.py:46-50` no declara otro status HTTP.
- Impacto: una sonda o consumidor que evalúe solo el status HTTP puede marcar saludable la integración cuando el backend está caído; si el cuerpo es el canal intencional de estado, el contrato debe indicarlo explícitamente.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: status HTTP y cuerpo de `GET /api/backend-health`.
- Cómo validarlo: acordar si la ruta es proxy o envoltorio de estado; probar upstream `200`, `503` y error de conexión, y afirmar el status HTTP y JSON requeridos en cada caso.

Baseline anterior a H-API-09: `python tools/lab.py test api` — 30 pruebas pasaron y cobertura total reportada de 100%. Tras implementar H-API-09, la suite reportó 52 pruebas pasadas y cobertura total de 100%; permanecen dos warnings de deprecación de dependencias.

## Contrato observado

El contrato observado se documenta en `docs/ENDPOINTS.md`; sus rutas y formatos derivan del código y no constituyen aprobación global. Para `POST /api/tasks`, H-API-09 acordó los catálogos exactos y el rechazo `422`; las demás decisiones de contrato siguen pendientes. Todas las rutas dependen de `legacy_identity` y requieren el header `Authorization` con token aceptado por esa función.

| método y ruta | contrato observado | contrato acordado | pendiente |
|---|---|---|---|
| `GET /api/tasks?owner=...` | `owner` es opcional; por defecto usa el username decodificado. Devuelve `200` y una lista de tareas con `id`, `title`, `description`, `status`, `owner`, `priority` y `createdAt`. | No documentado. | Confirmar contrato y autorización de `owner`. Evidencia: `api/app/routes.py:18-24`, `api/app/services.py:30-33`, `api/app/schemas.py:23-28`. |
| `POST /api/tasks` | Recibe JSON con defaults `title`/`description` vacíos, `status` `TODO`, `priority` `MEDIUM`, `owner` autenticado. `status` solo admite `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`; `priority` solo `LOW`, `MEDIUM`, `HIGH`; valores no exactos producen `422`. Devuelve `201` con el objeto de tarea. | Catálogos y rechazo `422` aprobados para H-API-09. | Confirmar otros campos/defaults según contrato de producto. Evidencia: `api/app/routes.py:25-30`, `api/app/schemas.py:15-32`, `api/app/services.py:37-50`. |
| `GET /api/summary?owner=...` | `owner` es opcional; por defecto usa el username decodificado. Devuelve `owner`, `total`, `byStatus` y `highPriorityOpen`. | No documentado. | Confirmar forma de respuesta y autorización de `owner`. Evidencia: `api/app/routes.py:32-37`, `api/app/services.py:40-55`, `api/app/schemas.py:31-35`. |
| `POST /api/requirements` | Recibe multipart con el campo `file`; devuelve `201` con `owner`, `fileName`, `storedAt` y `size`. | No documentado. | Confirmar límites y reglas de nombre/extensión. Evidencia: `api/app/routes.py:39-45`, `api/app/services.py:57-66`, `api/app/schemas.py:38-42`. |
| `GET /api/backend-health` | Consulta la URL de `AUTH_HEALTH_URL` (default `http://localhost:8080/q/health`) y devuelve `requestedBy`, `status` y `body`; ante excepción devuelve `status: 0` y mensaje genérico. | No documentado. | Confirmar formato de `body` y política del mensaje de error. Evidencia: `api/app/routes.py:46-50`, `api/app/services.py:68-86`, `api/app/schemas.py:45-48`. |