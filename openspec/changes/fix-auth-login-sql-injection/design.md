# Design

## Context

El componente `auth/` es un servicio Java 21 con Quarkus 3.27.4. `LegacyDatabase` usa JDBC contra SQLite, cuya URL proviene de `AUTH_DB_URL` y, si no está definida, apunta a `jdbc:sqlite:./data/workshop.db`. `findByCredentials` construye actualmente la búsqueda concatenando username y password y la ejecuta con `Statement`. El Issue #23 identifica que esa entrada puede alterar la consulta.

`AuthResource.login` delega la búsqueda en `LegacyDatabase`; cuando no recibe un usuario responde `401`, y cuando lo encuentra responde `200` con `token`, `expiresIn` y `user` (username, displayName y role), además del campo `debug` existente. La prueba `AuthResourceTest.logsInWithWorkshopUser` ya protege el login de `student`.

El contrato de login no está descrito en `docs/ENDPOINTS.md`, que cubre los endpoints `/api/...`. Por tanto, para este cambio el contrato adicional de `/auth/login` se toma del Issue #23 y del comportamiento actual que la propuesta exige preservar. No se modifica el contrato documentado de la API.

## Goals / Non-Goals

### Goals

- Evitar que username o password cambien la estructura o el significado de la búsqueda SQL, cumpliendo el criterio del Issue #23 de parametrizar ambos valores.
- Mantener el login válido de `student` y la respuesta HTTP existente.
- Rechazar intentos de inyección con `401` y sin devolver `token`.
- Limitar la implementación y sus pruebas a `auth/`.

### Non-Goals

- Cambiar la ruta, el formato de request, el formato de respuesta, la generación del token o la validación de campos de `POST /auth/login`.
- Cambiar el esquema o la persistencia de usuarios, migrar contraseñas, sustituir SQLite o añadir dependencias.
- Modificar `api/`, `web/`, `docs/ENDPOINTS.md` u otros hallazgos de seguridad.

## Protected Contracts

- `POST /auth/login` con `student` y `Workshop123!` sigue respondiendo `200`, con `user.username` igual a `student` y un `token` presente. También se conserva la estructura de respuesta existente.
- Credenciales incorrectas, incluidas las entradas de inyección descritas en la spec, responden `401` y no incluyen `token`.
- Los endpoints y expectativas de autenticación documentados en `docs/ENDPOINTS.md` no cambian.

## Affected Components

- `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`: único punto de acceso que forma y ejecuta la búsqueda por credenciales.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: pruebas de contrato HTTP para login válido y rechazo de intentos de inyección.
- `AuthResource` no requiere cambios de comportamiento: ya transforma una búsqueda sin coincidencias en `401` y conserva la respuesta de éxito.

No se prevén cambios en `pom.xml`, configuración, otros componentes ni documentos generales.

## Decisions

### Mantener una búsqueda SQL fija y enlazar ambos valores

La consulta conserva su estructura y recibe username y password como parámetros JDBC separados. El resultado continúa mapeándose al mismo `UserRecord`; no se cambia la semántica de la ruta ni la respuesta del recurso.

Esto cumple directamente el criterio del issue y evita que los caracteres del input se interpreten como sintaxis SQL. No requiere una nueva dependencia ni una migración de SQLite.

### Mantener la frontera de responsabilidades actual

El cambio queda en la búsqueda de `LegacyDatabase`. `AuthResource` sigue siendo responsable del status y la respuesta HTTP; no se agrega una detección de patrones de ataque en el recurso. Así, la regla de seguridad se aplica al punto donde se consulta la base y no depende de una lista de strings sospechosos.

### Alternativas consideradas

- Escapar comillas o caracteres especiales en el input: descartado porque depende de reglas de escape y deja la consulta acoplada a la sintaxis SQL; no satisface el criterio explícito de parametrización del issue.
- Rechazar inputs que contengan fragmentos SQL: descartado porque es una lista incompleta y puede rechazar valores legítimos sin garantizar que la consulta sea segura.
- Cambiar ORM, almacenamiento, esquema o formato de contraseñas: fuera de alcance; amplía el riesgo y no es necesario para corregir este hallazgo.

## Incremental Strategy

1. Antes de cambiar el comportamiento, registrar en `AuthResourceTest` el comportamiento válido ya existente y el rechazo de credenciales incorrectas ordinarias. La prueba de login válido existente debe mantenerse como protección del contrato.
2. Añadir pruebas de regresión para la inyección independiente en username y password. Cada caso debe comprobar `401` y ausencia de `token`; contra el código actual se espera que estas pruebas evidencien el defecto, no que su resultado vulnerable se acepte como contrato.
3. Aplicar el cambio mínimo a la búsqueda de credenciales en `LegacyDatabase`, sin modificar la API REST ni la representación de `UserRecord`.
4. Ejecutar `mvn test` desde `auth/`; revisar además la cobertura del código modificado con el gate de JaCoCo existente y la meta de 85% indicada para `auth/`. No silenciar scanners ni reducir gates.
5. Revisar que el diff funcional permanezca dentro de `auth/` y que los tres escenarios de login de la spec queden cubiertos.

## Tests and Characterization

- **Caracterización previa del login válido:** conservar `logsInWithWorkshopUser`, que verifica `200`, `user.username=student` y `token` no nulo; añadir aserciones solo si son necesarias para proteger los campos existentes sin cambiar el contrato.
- **Caracterización previa del rechazo ordinario:** comprobar credenciales válidas en forma pero incorrectas y verificar `401` sin token, comportamiento que ya proporciona `AuthResource` cuando la búsqueda no encuentra usuario.
- **Pruebas de regresión de seguridad:** comprobar por separado el payload con username `' OR '1'='1` y el payload con password `' OR '1'='1`; ambos deben devolver `401` sin token. No caracterizar la respuesta vulnerable actual como comportamiento esperado.
- **Validación del componente:** ejecutar `mvn test` desde `auth/`; generar/revisar JaCoCo mediante el ciclo Maven existente para verificar la meta de cobertura aplicable al código modificado.

## Risks / Trade-offs

- Un error en el orden o valor enlazado para los parámetros podría rechazar credenciales válidas. El test positivo existente y los tests de credenciales incorrectas detectan regresiones de contrato.
- La ruta usa una base SQLite local configurable; el resultado de pruebas puede depender del estado de `data/workshop.db`. La implementación debe conservar las mismas columnas y el mismo mapeo, sin introducir cambios de esquema.
- El manejo actual de errores JDBC captura excepciones y devuelve `null`, que el recurso interpreta como `401`. Este diseño no cambia ese comportamiento; mejorar la observabilidad o distinguir errores internos queda fuera del Issue #23.
- Las pruebas de inyección demuestran los casos comprometidos por el issue, pero no sustituyen análisis estático ni garantizan cobertura de todas las entradas. Los gates de seguridad existentes deben permanecer activos.

## Rollback

No se requiere migración ni cambio de datos, por lo que el cambio de código es técnicamente reversible. Sin embargo, restaurar la búsqueda previa reabre la vulnerabilidad reportada; el rollback no debe considerarse un estado final aceptable. Si una regresión bloquea el despliegue, preferir una corrección hacia delante. Cualquier reversión temporal debe limitarse al entorno afectado y acompañarse de una mitigación operativa antes de volver a exponer el login.