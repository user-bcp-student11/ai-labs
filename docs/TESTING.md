# Pruebas de auth

## Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /q/health` | El servicio responde y no hay checks registrados | Camino feliz | `200`; JSON `status: UP`, `checks: []`. |
| `GET /q/health` | Sondeos repetidos sin credenciales ni cuerpo | Borde | Cada sondeo devuelve `200` y `status: UP`. |
| `GET /q/health` | Error HTTP producido por la aplicación | Error | No hay respuesta de error de aplicación documentada; la ruta la sirve SmallRye Health y no hay checks locales que puedan devolver `DOWN`. No aplica una prueba de cuerpo de error. |
| `POST /auth/login` | Usuario `student` con `Workshop123!` y `client` presente | Camino feliz | `200`; token no nulo y perfil del usuario. |
| `POST /auth/login` | Credenciales válidas sin el campo opcional `client` | Borde | `200`; mismo perfil, token y campos de respuesta. |
| `POST /auth/login` | Cuerpo JSON `null` | Error 400 | `{"message":"Request is null"}`. |
| `POST /auth/login` | Falta `username` | Error 400 | `{"message":"Username is required"}`. |
| `POST /auth/login` | `username` contiene solo espacios | Error 400 | `{"message":"Username is required"}`. |
| `POST /auth/login` | Falta `password` | Error 400 | `{"message":"Password is required"}`. |
| `POST /auth/login` | `password` contiene solo espacios | Error 400 | `{"message":"Password is required"}`. |
| `POST /auth/login` | Usuario/contraseña no coinciden | Error 401 | `{"message":"Invalid user unknown or password"}`. |
| `POST /auth/login` | Username válido conocido con una comilla simple añadida | Borde/error 401 | `401`; no autentica. Este caso también protege la consulta parametrizada. |
| `POST /auth/login` | La búsqueda de credenciales lanza una excepción con mensaje | Error 500 | `500`; body contiene `message` y el nombre de clase en `exception`. |
| `POST /auth/login` | La búsqueda lanza una excepción sin mensaje | Error 500 | `500`; `message` es `Unknown error` y `exception` conserva el nombre de clase. |

No se inventaron pruebas de `DOWN` para health: la configuración actual no registra checks de aplicación y una indisponibilidad del proceso no puede responder con un body de ese endpoint. Los errores de JSON mal formado y `Content-Type` no aceptado tampoco tienen formato fijado por el código de auth; quedan pendientes de caracterización contra el runtime exacto antes de añadirlos como contrato.

## Código de pruebas de endpoint

Los siguientes métodos corresponden a `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` y `HealthResourceTest.java`. Las pruebas adicionales de hash y migración de contraseña siguen en `AuthResourceTest`; no se repiten aquí porque no son llamadas a un endpoint.

### `AuthResourceTest.java`

```java
@Test
void logsInWithWorkshopUser() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(200)
            .body("user.username", is("student"))
            .body("token", notNullValue());
}

@Test
void logsInWithoutOptionalClient() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(200)
            .body("user.username", is("student"))
            .body("user.displayName", is("Workshop Student"))
            .body("user.role", is("STUDENT"))
            .body("expiresIn", is(3600))
            .body("debug", is("authenticated-with-legacy-flow"))
            .body("token", notNullValue());
}

@Test
void rejectsNullLoginRequest() {
    given()
            .contentType("application/json")
            .body("null")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Request is null"));
}

@Test
void rejectsMissingUsername() {
    given()
            .contentType("application/json")
            .body("{\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Username is required"));
}

@Test
void rejectsBlankUsername() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"  \",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Username is required"));
}

@Test
void rejectsMissingPassword() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Password is required"));
}

@Test
void rejectsBlankPassword() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"  \"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Password is required"));
}

@Test
void rejectsInvalidCredentials() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"unknown\",\"password\":\"wrong\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(401)
            .body("message", is("Invalid user unknown or password"));
}

@Test
void rejectsUsernameContainingSingleQuote() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student'\",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(401);
}

@Test
void returnsInternalServerErrorWhenCredentialLookupThrows() {
    assertCredentialLookupFailure(
            new IllegalStateException("Controlled test failure"),
            "Controlled test failure");
}

@Test
void usesGenericMessageWhenCredentialLookupFailureHasNoMessage() {
    assertCredentialLookupFailure(new IllegalStateException(), "Unknown error");
}

private void assertCredentialLookupFailure(RuntimeException failure, String expectedMessage) {
    AuthResource resource = new AuthResource();
    resource.database = new LegacyDatabase() {
        @Override
        public UserRecord findByCredentials(String username, String password) {
            throw failure;
        }
    };
    LoginRequest request = new LoginRequest();
    request.username = "student";
    request.password = "Workshop123!";

    try (Response response = resource.login(request)) {
        assertEquals(500, response.getStatus());
        assertEquals(Map.of(
                "message", expectedMessage,
                "exception", failure.getClass().getName()), response.getEntity());
    }
}
```

### `HealthResourceTest.java`

```java
@Test
void reportsApplicationUpWithNoRegisteredChecks() {
    given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("status", is("UP"))
            .body("checks", hasSize(0));
}

@Test
void supportsRepeatedHealthProbesWithoutAuthentication() {
    for (int probe = 0; probe < 2; probe++) {
        given()
                .when().get("/q/health")
                .then()
                .statusCode(200)
                .body("status", is("UP"));
    }
}
```

## Ejecuciones y cobertura

| componente | IDs/casos | comando y directorio | código de salida | resultado real |
|---|---|---|---:|---|
| auth | H-AUTH-01, H-AUTH-02; línea base antes de estas pruebas de endpoint | `mvn test`; directorio `auth/`; `AUTH_DB_URL=jdbc:sqlite:./target/test-docs-baseline.db` | 0 | 5 pruebas, 0 fallos, 0 errores. |
| auth | H-AUTH-01, H-AUTH-02 y casos de `GET /q/health`, `POST /auth/login` | `mvn test`; directorio `auth/` | 0 | 15 pruebas, 0 fallos, 0 errores. |
| auth | H-AUTH-01, H-AUTH-02 y todos los casos anteriores | `mvn verify`; directorio `auth/` | 0 | 15 pruebas, 0 fallos, `BUILD SUCCESS`; generó `auth/target/site/jacoco/index.html` y `jacoco.csv`. |

**Método de cobertura:** JaCoCo 0.8.12 configurado en `auth/pom.xml`; se leyó `auth/target/site/jacoco/jacoco.csv`. Por clase de producción relevante al flujo: `AuthResource` 25/25 líneas (100%) y 14/14 ramas (100%); `LegacyDatabase` 49/55 líneas (89,1%); `PasswordHasher` 34/36 líneas (94,4%). Los tres resultados superan 85%. No se modificó código de producción en este paso.

## Fallos, pendientes y propuestas

- **Fallos ejecutados:** ninguno en la suite final.
- **Pendiente:** simular un estado `DOWN`/fallo de infraestructura para health requiere definir un health check y su contrato; la aplicación actual no define uno, así que no se añadió una prueba que invente ese comportamiento.
- **Pendiente:** capturar respuestas de JSON mal formado y `Content-Type` no admitido del runtime Quarkus/RESTEasy específico; `auth/` no define esos cuerpos.
- **Propuestas:** documentar y probar esos resultados después de acordar el contrato de errores del framework; no se reportan como ejecutados.
