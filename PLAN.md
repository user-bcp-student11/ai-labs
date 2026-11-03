# Plan

## API

Estado: aprobado según confirmación del usuario el 2026-11-02; implementación iniciada el mismo día. Alcance de código, configuración y pruebas limitado a `api/`.

### Límites y secuencia

- No existe `docs/ENDPOINTS.md`. Mantener las cinco rutas y sus métodos, los códigos/campos de las respuestas exitosas y los defaults observados en `HALLAZGOS.md`.
- La autorización por identidad, el rechazo de tokens inválidos, los errores genéricos y el rechazo de archivos inseguros son cambios intencionales respecto al comportamiento inseguro observado y quedan aprobados como parte de este plan. Registrar en el contrato los estados/cuerpos de error y los criterios de aceptación de archivos acordados antes de implementar esos cambios.
- Escribir primero en `api/tests/test_api.py` las caracterizaciones de los flujos válidos y sus respuestas. Luego extraer capas sin cambiar esos resultados; aplicar después las correcciones de SQL y autorización. Tratar JWT como bloqueado hasta acordar el contrato con el emisor externo, sin leer ni modificar otros componentes. Acordar también allowlist de extensiones y tamaño máximo antes de implementar la carga segura.
- Preservar la factoría `create_app(db_path, upload_dir)` para aislar SQLite y archivos en pruebas. Usar secretos ficticios solo en pruebas; ningún secreto real en código o evidencias.

### H-API-01 — Token Base64 sin firma

- **Hallazgo:** Base64 con secreto constante embebido y sin firma criptográfica.
- **Problema:** decodificar y comparar texto no autentica la integridad del token. No hay verificación de emisor ni audiencia; aceptar el formato actual junto al nuevo mantendría la vulnerabilidad.
- **Cambio propuesto:** verificar JWT firmado con una biblioteca mantenida (PyJWT, dependencia nueva justificada porque evita implementar manualmente el estándar). Configurar algoritmo permitido, clave y valores esperados de emisor/audiencia mediante entorno; exigir `exp` y claims de identidad. Fallar de forma cerrada si falta configuración. No admitir fallback al token Base64.
- **Dependencia externa:** acordar con el emisor el algoritmo, clave pública/secreta, `iss`, `aud` y claims antes de cambiar el validador. Este acuerdo puede requerir una actualización coordinada fuera del alcance `api/`; no se asumirá que puede hacerse unilateralmente.
- **Archivos a tocar:** `api/app/main.py`; nuevo `api/app/security.py`; `api/requirements.txt`; `api/tests/test_api.py`.
- **Caracterización previa:** probar autenticación válida con el token de prueba actual y respuesta `401` para token inválido, conservando las respuestas exitosas de las rutas. Después del acuerdo, añadir casos JWT válido, expirado, firma alterada, emisor/audiencia incorrectos y configuración ausente. Actualizar la fixture a JWT firmado con clave ficticia.

### H-API-02 — Autorización de tareas controlada por el cliente

- **Hallazgo:** `owner` permite consultar y crear tareas asociadas a otra identidad.
- **Problema:** las rutas confían en datos del query/body en vez de vincular el acceso al `username` autenticado.
- **Cambio propuesto:** usar siempre la identidad verificada para seleccionar el propietario. Mantener el query `owner` y el campo opcionales por compatibilidad de forma; si se envían con un propietario distinto, rechazar la operación con un error genérico `403`. No inventar privilegios por `role`; cualquier política de roles requiere acuerdo explícito.
- **Archivos a tocar:** nuevo `api/app/services.py` y `api/app/repositories.py` según H-API-06; `api/app/routes.py` según H-API-06; `api/tests/test_api.py`.
- **Caracterización previa:** guardar pruebas de listado y resumen del usuario autenticado y creación con propietario por defecto, verificando estado, claves y valores de respuesta. Añadir una prueba de regresión que primero documente el acceso cruzado actual y luego se cambie para exigir rechazo; no conservar el acceso vulnerable como expectativa.

### H-API-03 — SQL por concatenación

- **Hallazgo:** filtros e inserts se construyen concatenando valores recibidos.
- **Problema:** datos externos pueden cambiar la sintaxis o el resultado de consultas SQLite.
- **Cambio propuesto:** centralizar SQL en repositorio y usar placeholders `?` con parámetros para filtros, inserts y consultas por ID. Evitar duplicar la lista de columnas/mapper de tareas; mantener el orden y las claves de respuesta existentes.
- **Archivos a tocar:** nuevo `api/app/repositories.py`; `api/app/main.py` y nuevo `api/app/routes.py` por H-API-06; `api/tests/test_api.py`.
- **Caracterización previa:** comprobar listado, creación y resumen con datos normales y preservar IDs, defaults, códigos HTTP y forma JSON. Añadir una prueba de regresión con texto que incluya comillas y verificar que se almacena como dato literal, no como parte de SQL.

### H-API-04 — Carga de archivos insegura

- **Hallazgo:** se usa `file.filename` directamente y no se limita la lectura.
- **Problema:** un nombre manipulado puede escapar del directorio de uploads; una carga grande puede consumir memoria o almacenamiento.
- **Cambio propuesto:** validar y normalizar el nombre, guardar dentro del directorio configurado, aceptar solo una allowlist acordada y limitar bytes leídos antes de persistir. Definir los límites mediante configuración con nombres claros, no números mágicos. Mantener la ruta, multipart `file` y las claves `owner`, `fileName`, `storedAt` y `size` en la respuesta exitosa.
- **Pendiente de decisión:** `requirements.txt` está cubierto por la prueba actual, pero no define la allowlist ni el límite máximo. Acordarlos antes de implementar; no extenderlos por inferencia.
- **Archivos a tocar:** nuevo `api/app/services.py` o módulo acotado de almacenamiento según H-API-06; `api/app/routes.py`; `api/app/config.py` solo si la configuración requiere un módulo propio; `api/tests/test_api.py`.
- **Caracterización previa:** preservar carga válida de `requirements.txt`, estado `201`, claves/tipos de la respuesta y archivo persistido. Añadir regresiones para ruta/nombre inválidos, extensión no permitida y tamaño sobre límite; verificar que no se escribe fuera del directorio.

### H-API-05 — Dependencias pendientes de análisis SCA

- **Hallazgo:** versiones fijadas de `urllib3` y `python-multipart` sin evidencia de revisión SCA.
- **Problema:** no se puede determinar la aplicabilidad ni el riesgo real solo leyendo las versiones; actualizar sin advisory puede introducir cambios innecesarios o incompatibles.
- **Cambio propuesto:** capturar primero un informe del scanner de dependencias disponible con paquetes, versiones, advisory, rango afectado y justificación. Actualizar solo a versiones corregidas compatibles con Python 3.13 y FastAPI; conservar pins reproducibles y no silenciar findings. No declarar CVE hasta que el informe lo confirme.
- **Evidencia SCA obtenida:** baseline `pip-audit` reportó advisories para `urllib3==2.5.0`, `python-multipart==0.0.21` y la transitiva `starlette==0.50.0`. FastAPI `0.128.2` impedía la versión corregida de Starlette; la resolución simulada confirmó compatibilidad de `fastapi==0.140.0`, `starlette==1.3.1`, `urllib3==2.8.0` y `python-multipart==0.0.31`. Esos pins están aplicados en `api/requirements.txt`; el scan posterior no encontró vulnerabilidades conocidas.
- **Archivos a tocar:** `api/requirements.txt`; `api/requirements-dev.txt` únicamente si el scanner elegido se incorpora justificadamente al entorno de desarrollo; `api/tests/test_api.py` solo si una actualización requiere adaptar comportamiento.
- **Caracterización previa:** obtener y conservar el escaneo de las dependencias actuales como baseline antes de editar pins. No hay una prueba funcional que caracterice un CVE; el baseline SCA es la verificación previa adecuada. Después, repetir el mismo scanner y ejecutar la suite API.

### H-API-06 — Responsabilidades concentradas en `main.py`

- **Hallazgo:** aplicación, SQLite, endpoints, reglas y serialización están en un módulo.
- **Problema:** los límites mezclados hacen difícil probar las reglas aisladas y aumentan el riesgo de regresión al corregir seguridad.
- **Cambio propuesto:** mantener `main.py` como composición de la app y conservar `create_app(db_path, upload_dir)`. Extraer rutas a `routes.py`, acceso SQLite/esquema a `repositories.py`, reglas a `services.py` y validación/serialización a `schemas.py`. Mover autenticación a `security.py` para H-API-01. Cada función debe tener una responsabilidad y las rutas no deben ejecutar SQL.
- **Archivos a tocar:** `api/app/main.py`; nuevos `api/app/routes.py`, `api/app/repositories.py`, `api/app/services.py`, `api/app/schemas.py` y `api/app/security.py`; `api/tests/test_api.py`.
- **Caracterización previa:** ampliar `api/tests/test_api.py` para fijar los cinco métodos/rutas, sus códigos y las respuestas exitosas observadas: lista de tareas, creación, resumen, carga válida y formato de backend health con dependencia HTTP simulada. Mantener pruebas aisladas con `tmp_path` y cerrar conexiones mediante el ciclo de vida de la app.

### H-API-07 — Tipado, errores y lógica compleja

- **Hallazgo:** entrada/salida con `dict` y `Any`, capturas amplias, anidamiento y duplicación.
- **Problema:** validación débil, errores internos expuestos y reglas difíciles de mantener.
- **Cambio propuesto:** definir modelos Pydantic request/response con defaults compatibles y alias `createdAt` para conservar JSON. Extraer contadores y decisiones del resumen a funciones pequeñas con retornos claros; reutilizar el mapper/consulta de tarea. Capturar excepciones específicas, registrar detalles solo en servidor y devolver mensaje genérico al cliente. Mantener códigos y esquemas de éxito; revisar explícitamente el cambio del cuerpo de error de token inválido antes de implementarlo.
- **Archivos a tocar:** nuevo `api/app/schemas.py`; `api/app/services.py`, `api/app/routes.py` y `api/app/security.py` según H-API-06/H-API-01; `api/tests/test_api.py`.
- **Caracterización previa:** verificar defaults actuales de creación, claves y tipos de todas las respuestas exitosas, reglas actuales del resumen y estado `401` para token inválido. Añadir casos de entrada válida y malformada; preservar la forma exitosa y confirmar con revisión humana cualquier cambio de errores detallados a mensaje genérico.

## Verificación prevista

Después de implementar cada bloque aprobado, ejecutar pruebas desde `api/` con `python -m pytest`; para cobertura, usar `python -m pytest --cov=app --cov-report=term-missing`. Registrar resultados reales por componente e IDs en `docs/TESTING.md` cuando ese artefacto se cree. No cambiar el umbral de cobertura; revisar el código modificado frente a la meta del 85% y mantener visibles fallos o verificaciones no ejecutadas.

## Ejecuciones registradas

- 2026-11-02 — componente `api`, IDs H-API-01 a H-API-07: baseline previo con `python -m pytest` usando el intérprete de `api/.venv`: **4 passed**, 11 warnings. La invocación inicial con Python del sistema no encontró `pytest`; no contó como ejecución de pruebas.
- 2026-11-02 — componente `api`, IDs H-API-02, H-API-03, H-API-06 y H-API-07: caracterizaciones de rutas, defaults, `owner` actual y forma de respuesta: **8 passed**, 19 warnings antes del cambio de SQL.
- 2026-11-02 — componente `api`, ID H-API-03: `tests/test_api.py::test_create_task_stores_quotes_as_literal_text` falló antes del cambio con `sqlite3.OperationalError` en el `INSERT` concatenado; tras parametrizar filtros, inserción y lectura por ID, la misma prueba dio **1 passed** y la suite dio **9 passed**, 21 warnings.
- 2026-11-02 — componente `api`, ID H-API-06: extracción modular; la primera suite tuvo 8 passed y un fallo del monkeypatch antiguo, corregido al parchear `app.services.urllib3`; suite posterior: **9 passed**, 1 warning.
- 2026-11-02 — componente `api`, ID H-API-02: las pruebas de override fallaron antes del cambio (`200` y `201` en lugar de `403`); después, las dos pruebas dirigidas dieron **2 passed** y la suite completa **9 passed**, 1 warning.
- 2026-11-02 — componente `api`, ID H-API-05: baseline SCA `python -m pip_audit -r requirements.txt`: **32 entradas de advisory en 3 paquetes** (`urllib3`, `python-multipart` y `starlette`); salida con código 1 por hallazgos. `pip-audit` se instaló únicamente en `api/.venv`, sin cambiar manifiestos. No hay remediación SCA confirmada todavía.
- 2026-11-02 — componente `api`, ID H-API-07: caracterizaciones previas confirmaron detalle de excepción en `401` y backend health; las pruebas genéricas fallaron antes del cambio y después pasaron. Suite posterior: **11 passed**; caso adicional de payload no objeto: **1 passed**.
- 2026-11-02 — componente `api`, ID H-API-05: tras fijar FastAPI `0.140.0`, Starlette `1.3.1`, urllib3 `2.8.0` y python-multipart `0.0.31`, la suite dio **11 passed** y `pip-audit -r requirements.txt` informó **No known vulnerabilities found**.
- 2026-11-02 — componente `api`, IDs H-API-01 a H-API-07: `python -m pytest --cov=app --cov-report=term-missing`: **13 passed**, cobertura total **99%** (188 statements, 1 missed); `app/security.py` quedó en 90%. Dos warnings de deprecación de `starlette.testclient`/`httpx` y `anyio` permanecen visibles.
- H-API-01 y H-API-04 siguen pendientes. H-API-01 requiere acuerdo externo del contrato JWT; H-API-04 requiere acordar allowlist y tamaño. No se modificaron esos flujos ni se afirmaron sus correcciones.
- Revisión local 2026-11-02 — componente `api`, H-API-02 reabierto: las rutas rechazan `owner` distinto, pero `identity.username` aún se deriva del token Base64 sin firma de H-API-01 (`api/app/security.py:10,14-24`). Las pruebas `api/tests/test_api.py:82-100` usan la misma fixture legacy y no acreditan una identidad confiable. Mantener H-API-02 `Pendiente` hasta verificar JWT y repetir autorización con identidades firmadas.