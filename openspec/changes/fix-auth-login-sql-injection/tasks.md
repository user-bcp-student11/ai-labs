# Tasks

## 1. Caracterizar el contrato y preparar regresiones en auth/

- [x] 1.1 Ejecutar y registrar el baseline de `AuthResourceTest.logsInWithWorkshopUser` antes de cambiar el comportamiento; verificar desde `auth/` con `mvn -Dtest=AuthResourceTest test` que responde `200`, `user.username=student` y `token` no nulo.
- [x] 1.2 Añadir a `AuthResourceTest` un caso de credenciales ordinarias incorrectas; verificar con `mvn -Dtest=AuthResourceTest test` que responde `401` y no incluye `token`.
- [x] 1.3 Añadir casos de regresión separados para la inyección en username y password, verificando en cada uno `401` y ausencia de `token`; antes de la implementación, confirmar con `mvn -Dtest=AuthResourceTest test` que los casos de ataque exponen el comportamiento vulnerable actual, sin aceptarlo como contrato.

## 2. Parametrizar la búsqueda y validar auth/

- [x] 2.1 Cambiar únicamente `LegacyDatabase.findByCredentials` para enviar username y password como parámetros separados, manteniendo el mapeo actual a `UserRecord`; verificar que `mvn -Dtest=AuthResourceTest test` pasa con los casos válido, inválido y ambos casos de inyección.
- [x] 2.2 Ejecutar `mvn test` desde `auth/`; verificar salida exitosa para el conjunto de pruebas del componente.
- [x] 2.3 Ejecutar `mvn verify` desde `auth/` y revisar el reporte JaCoCo para confirmar al menos 85% de cobertura en el código modificado; revisar también que el diff funcional queda limitado a `auth/` y no agrega supresiones de scanners ni reduce quality gates.