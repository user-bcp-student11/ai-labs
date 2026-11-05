# Capability: auth-login

## ADDED Requirements

### Requirement: El login solo acepta credenciales literales

El flujo de autenticación MUST tratar username y password como valores de credencial. El contenido de esos valores MUST NOT alterar la búsqueda de usuarios ni autenticar a una cuenta distinta de la que coincide con ambas credenciales.

#### Scenario: Una inyección en username no autentica

- WHEN el cliente envía `POST /auth/login` con username `' OR '1'='1` y password `Workshop123!`
- THEN el servidor responde `401 Unauthorized`
- AND la respuesta no contiene el campo `token`

#### Scenario: Una inyección en password no autentica

- WHEN el cliente envía `POST /auth/login` con username `student` y password `' OR '1'='1`
- THEN el servidor responde `401 Unauthorized`
- AND la respuesta no contiene el campo `token`

### Requirement: El login válido conserva su contrato

El cambio MUST preservar la autenticación válida descrita por el Issue #23 y no cambiar el contrato de `POST /auth/login`.

#### Scenario: El usuario del taller inicia sesión

- WHEN el cliente envía `POST /auth/login` con username `student` y password `Workshop123!`
- THEN el servidor responde `200 OK`
- AND `user.username` es `student`
- AND la respuesta contiene un `token`