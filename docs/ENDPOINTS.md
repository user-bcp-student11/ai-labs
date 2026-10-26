# Contratos HTTP

## Estado del contrato de auth

- **Contrato observado:** lo que sigue se deriva de `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`, `LoginRequest.java`, `LegacyTokenUtil.java`, `LegacyDatabase.java`, la configuración y la extensión SmallRye Health declarada en `auth/pom.xml`.
- **Contrato acordado:** no se encontró un documento previo ni evidencia de un acuerdo independiente. Esta página registra el comportamiento observado, no una aprobación de compatibilidad externa.
- **Riesgos pendientes:** el token de login es Base64 sin firma; el error 500 expone detalles de excepción; CORS permite cualquier origen; una falla durante la migración de contraseñas puede dejar datos legados sin migrar. Consultar las notas de seguridad de cada endpoint.

## GET /q/health

### 1. Qué hace
Informa el estado agregado de salud de la aplicación de autenticación para que un consumidor local o un monitor de despliegue determine si está disponible.

### 2. Autenticación
No requiere autenticación ni un header `Authorization`. La ruta la aporta la extensión `quarkus-smallrye-health` (`auth/pom.xml:38-41`); no hay un recurso de autenticación que aplique autorización a este endpoint.

### 3. Request
Es `GET`, no recibe cuerpo JSON ni parámetros de ruta/query definidos por `auth/`.

| campo | tipo | obligatorio | descripción |
|---|---|---|---|
| — | — | No | Sin campos ni cuerpo de request definidos por la aplicación. |

Ejemplo de request: `GET /q/health` sin cuerpo.

### 4. Response exitosa
Con la extensión habilitada y sin health checks registrados en el componente, la respuesta es `200` con estado `UP` y lista `checks` vacía. La guía oficial de SmallRye Health describe estos dos campos y la lista vacía cuando no hay checks; esta aplicación declara la extensión en `auth/pom.xml:38-41` y no contiene implementaciones propias de health check.

| campo | tipo | descripción |
|---|---|---|
| `status` | string | Estado agregado; en el caso actual sin checks registrados es `UP`. |
| `checks` | array de objetos | Checks individuales; actualmente vacío. |

```json
{
  "status": "UP",
  "checks": []
}
```

### 5. Respuestas de error
No se encontraron respuestas de error construidas por código de la aplicación para esta ruta. Si el proceso no puede aceptar la solicitud, no hay una respuesta HTTP del servicio que se pueda documentar como cuerpo JSON. No se documenta `DOWN` como respuesta actual porque `auth/` no registra health checks que lo produzcan.

| estado | cuándo ocurre | cuerpo de ejemplo |
|---|---|---|
| — | No hay error HTTP de aplicación comprobable en el código actual. La respuesta de indisponibilidad del proceso o de infraestructura queda fuera del endpoint. | No aplica: el proceso no entrega un cuerpo HTTP de aplicación. |

**Pregunta abierta:** si el despliegue registra health checks externos o habilita una interfaz de administración, ¿qué respuestas y rutas adicionales deben formar parte del contrato de ese entorno?

### 6. Notas de seguridad
La ruta expone información de disponibilidad sin autenticación, como es habitual para health checks. CORS está habilitado globalmente y `auth/src/main/resources/application.properties:4-7` configura el origen `/.*/`; el control de acceso a esta ruta no debe depender de CORS.

## POST /auth/login

### 1. Qué hace
Autentica a una persona usuaria con sus credenciales y, si coinciden, devuelve su perfil básico y un valor de token para la sesión.

### 2. Autenticación
No requiere autenticación previa ni un header `Authorization`; es el endpoint que inicia la sesión. El recurso define `POST /auth/login` en `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:15-24`.

### 3. Request
Enviar `Content-Type: application/json`. Los campos `username` y `password` deben existir como strings no nulos ni vacíos/blancos; `client` es opcional y el código de autenticación no lo consulta. Campos y validación: `auth/src/main/java/com/bcp/workshop/auth/LoginRequest.java:3-6` y `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:26-35`.

| campo | tipo | obligatorio | descripción |
|---|---|---|---|
| `username` | string | Sí | Nombre de usuario; se rechaza si falta, es nulo o queda vacío tras `trim()`. |
| `password` | string | Sí | Contraseña; se rechaza si falta, es nula o queda vacía tras `trim()`. Se valida con PBKDF2 contra el hash almacenado (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:93-103`). |
| `client` | string | No | Campo aceptado por `LoginRequest`; no interviene en la autenticación ni modifica la respuesta. |

Ejemplo con las credenciales ficticias locales sembradas por `LegacyDatabase` (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:20-21,55-57`):

```json
{
  "username": "student",
  "password": "Workshop123!",
  "client": "angular-workshop"
}
```

### 4. Response exitosa
Si las credenciales coinciden, devuelve `200`. El cuerpo lo construye `AuthResource` (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:39-50`); el usuario proviene de `UserRecord` (`auth/src/main/java/com/bcp/workshop/auth/UserRecord.java:3`). `displayName` se escapa con `escapeHtml4` antes de serializarse.

| campo | tipo | descripción |
|---|---|---|
| `token` | string | Token generado para el usuario y rol actuales. Es una cadena Base64, no un JWT firmado. |
| `expiresIn` | integer | Duración anunciada en segundos; el recurso devuelve `3600`. |
| `user` | object | Perfil de la persona autenticada. |
| `user.username` | string | Nombre de usuario autenticado. |
| `user.displayName` | string | Nombre visible, escapado con `StringEscapeUtils.escapeHtml4`. |
| `user.role` | string | Rol almacenado para el usuario. |
| `debug` | string | Marcador fijo `authenticated-with-legacy-flow` presente en la respuesta actual. |

Ejemplo JSON completo; el token es un valor de muestra calculado por el formato actual y cambia con el instante de emisión:

```json
{
  "token": "c3R1ZGVudHxTVFVERU5UfDE3OTMwNTQ2NzJ8V09SS1NIT1BfU0VDUkVUXzIwMjY=",
  "expiresIn": 3600,
  "user": {
    "username": "student",
    "displayName": "Workshop Student",
    "role": "STUDENT"
  },
  "debug": "authenticated-with-legacy-flow"
}
```

### 5. Respuestas de error
El recurso construye estas respuestas (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:26-38,54-58`):

| estado | cuándo ocurre | cuerpo de ejemplo |
|---|---|---|
| 400 | El cuerpo JSON se convierte en `null`. | `{"message":"Request is null"}` |
| 400 | `username` falta, es nulo o vacío/blanco. | `{"message":"Username is required"}` |
| 400 | `password` falta, es nula o vacía/blanca. | `{"message":"Password is required"}` |
| 401 | No hay usuario con el nombre recibido o la contraseña no coincide. El repositorio también devuelve `null` cuando atrapa una excepción SQL; ese caso termina en el mismo 401. | `{"message":"Invalid user student or password"}` |
| 500 | Una excepción alcanza el `catch` del recurso. `message` usa el mensaje de la excepción o `Unknown error`; `exception` contiene el nombre de su clase. Los valores concretos dependen de la excepción. | `{"message":"Unknown error","exception":"java.lang.Exception"}` (forma posible cuando el mensaje es nulo; no es un texto fijo del endpoint). |

El manejador JAX-RS/Quarkus también puede producir errores de transporte o deserialización (por ejemplo, JSON mal formado o un `Content-Type` no aceptado por `@Consumes`). El código de aplicación no define sus cuerpos; la forma exacta debe comprobarse para la versión/runtime desplegado antes de tratarla como contrato.

### 6. Notas de seguridad
- La contraseña se compara contra PBKDF2-HMAC-SHA256 con salt aleatorio en `auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java:16-45`; las contraseñas legadas se migran durante la inicialización en `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:29-88`. La migración puede fallar y el `catch` permite continuar el arranque, por lo que este riesgo sigue pendiente.
- `token` es Base64 de username, rol, expiración y un secreto fijo; Base64 no firma ni protege integridad (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,12-15`). Aunque incluye un timestamp de una hora, el código de `auth/` no valida ese token ni su expiración. No usarlo como credencial verificable fuera del flujo local actual.
- El error 401 incorpora el username recibido, y el error 500 puede exponer mensaje y nombre de clase (`AuthResource.java:37,54-58`).
- CORS acepta cualquier origen mediante `/.*/` (`auth/src/main/resources/application.properties:4-7`).

## Preguntas abiertas

- ¿Se deben estandarizar los cuerpos de errores de deserialización y `Content-Type` no aceptado antes de considerarlos parte del contrato público?
- ¿Qué formato de token y mecanismo de validación debe acordarse antes de que otros componentes dependan de `token`?
