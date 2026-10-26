package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.hasSize;

@QuarkusTest
class HealthResourceTest {
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
}