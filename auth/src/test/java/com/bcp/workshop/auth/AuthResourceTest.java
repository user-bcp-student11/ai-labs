package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import jakarta.ws.rs.core.Response;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class AuthResourceTest {
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
    private static final String LEGACY_USERNAME = "legacy-existing";
    private static final String LEGACY_PASSWORD = "LegacyOnly123!";
    private static final String PASSWORD_HASH_PREFIX = "pbkdf2-sha256$";

    @Inject
    LegacyDatabase database;

    @Inject
    PasswordHasher passwordHasher;

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
    void preservesExistingCredentialsDuringInitialization() throws Exception {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT OR REPLACE INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)")) {
            statement.setString(1, LEGACY_USERNAME);
            statement.setString(2, LEGACY_PASSWORD);
            statement.setString(3, "Legacy User");
            statement.setString(4, "STUDENT");
            statement.executeUpdate();
        }

        database.initialize();

        String storedPassword;
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username=?")) {
            statement.setString(1, LEGACY_USERNAME);
            try (ResultSet result = statement.executeQuery()) {
                assertTrue(result.next());
                storedPassword = result.getString("password");
            }
        }

        assertTrue(storedPassword.startsWith(PASSWORD_HASH_PREFIX));
        assertNotEquals(LEGACY_PASSWORD, storedPassword);

        database.initialize();

        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username=?")) {
            statement.setString(1, LEGACY_USERNAME);
            try (ResultSet result = statement.executeQuery()) {
                assertTrue(result.next());
                assertEquals(storedPassword, result.getString("password"));
            }
        }

        given()
                .contentType("application/json")
                .body("{\"username\":\"" + LEGACY_USERNAME + "\",\"password\":\"" + LEGACY_PASSWORD + "\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is(LEGACY_USERNAME));
    }

    @Test
    void hashesPasswordsWithUniqueSaltsAndVerifiesThem() {
        String firstHash = passwordHasher.hash(LEGACY_PASSWORD);
        String secondHash = passwordHasher.hash(LEGACY_PASSWORD);

        assertNotEquals(firstHash, secondHash);
        assertTrue(passwordHasher.verify(LEGACY_PASSWORD, firstHash));
        assertFalse(passwordHasher.verify("wrong-password", firstHash));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "invalid-hash"));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, null));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "unknown$600000$c2FsdA$aGFzaA=="));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "pbkdf2-sha256$0$c2FsdA$aGFzaA=="));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "pbkdf2-sha256$1$c2FsdA$aGFzaA=="));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "pbkdf2-sha256$invalid$c2FsdA$aGFzaA=="));
        assertFalse(passwordHasher.verify(LEGACY_PASSWORD, "pbkdf2-sha256$600000$!$aGFzaA=="));
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
        assertCredentialLookupFailure(new IllegalStateException("Controlled test failure"), "Controlled test failure");
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
}
