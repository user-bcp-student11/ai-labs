# Change: fix-auth-login-sql-injection

## Why

El [Issue #23](https://github.com/user-bcp-student11/ai-labs/issues/23) reporta que el login compara credenciales mediante una consulta vulnerable a inyección SQL. Un valor manipulado puede alterar la búsqueda y permitir autenticación sin conocer la contraseña; corregirlo evita el acceso no autorizado.

## What Changes

- El login solo autentica cuando username y password corresponden literalmente a una cuenta.
- Se cumple el criterio comprometido por el issue de enviar ambos valores al lookup como parámetros SQL, no concatenarlos en el texto de la consulta. La elección de cambios técnicos adicionales queda para la implementación.
- Se conserva la respuesta de login exitoso indicada por el issue.

## Scope

### In scope

- Componente `auth/`: verificación de credenciales para `POST /auth/login` y escenarios de autenticación relacionados.
- Rechazo de intentos de inyección en username o password.

### Out of scope

- Cambios en `api/`, `web/`, otros componentes o endpoints.
- Rediseño del token, del almacenamiento de usuarios, de la validación de campos o de la respuesta de login.
- Otros hallazgos de seguridad que no estén incluidos en el Issue #23.

## Preserved Behavior and Baseline

- El login con `student` y `Workshop123!` continúa respondiendo `200`, con `user.username` igual a `student` y un `token` presente, según el Issue #23 y la prueba existente.
- `docs/ENDPOINTS.md` documenta los endpoints `/api/...` y el uso de `Authorization: Bearer <token>` por sus consumidores; no documenta `POST /auth/login`. Este cambio no modifica ese contrato de API. Los escenarios de login que faltan en el documento se toman del Issue #23, sin cambiar el flujo exitoso existente.

## Verifiable Acceptance Criteria

- Una autenticación válida conserva el status y los campos de respuesta indicados arriba.
- Inyección en username o password produce `401 Unauthorized` y la respuesta no incluye `token`.
- El lookup cumple el criterio del issue de parametrizar username y password.