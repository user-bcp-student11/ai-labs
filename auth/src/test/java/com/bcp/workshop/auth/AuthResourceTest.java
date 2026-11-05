package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@QuarkusTest
class AuthResourceTest {
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

    // Caracteriza el rechazo ya existente para credenciales incorrectas ordinarias (sin inyección).
    @Test
    void rejectsIncorrectPassword() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"WrongPassword123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }

    // Regresión de seguridad del Issue #23 (Requirement "login solo acepta credenciales literales", escenario username).
    @Test
    void rejectsSqlInjectionInUsername() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"' OR '1'='1\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }

    // Regresión de seguridad del Issue #23 (Requirement "login solo acepta credenciales literales", escenario password).
    @Test
    void rejectsSqlInjectionInPassword() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"' OR '1'='1\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }
}
