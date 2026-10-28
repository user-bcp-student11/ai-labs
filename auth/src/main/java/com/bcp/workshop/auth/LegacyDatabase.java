package com.bcp.workshop.auth;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class LegacyDatabase {
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
    private static final String STUDENT_USERNAME = "student";
    private static final String STUDENT_PASSWORD = "Workshop123!";
    private static final String TRAINER_USERNAME = "trainer";
    private static final String TRAINER_PASSWORD = "Trainer123!";

    @Inject
    PasswordHasher passwordHasher;

    @PostConstruct
    void initialize() {
        try {
            Files.createDirectories(Path.of("data"));
            try (Connection connection = DriverManager.getConnection(DB_URL)) {
                connection.setAutoCommit(false);
                try {
                    createSchema(connection);
                    seedUsers(connection);
                    migratePlaintextPasswords(connection);
                    connection.commit();
                } catch (Exception error) {
                    connection.rollback();
                    throw error;
                }
            }
        } catch (Exception error) {
            error.printStackTrace();
        }
    }

    private void createSchema(Connection connection) throws Exception {
        try (Statement statement = connection.createStatement()) {
            statement.executeUpdate("CREATE TABLE IF NOT EXISTS legacy_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL)");
        }
    }

    private void seedUsers(Connection connection) throws Exception {
        seedUser(connection, STUDENT_USERNAME, STUDENT_PASSWORD, "Workshop Student", "STUDENT");
        seedUser(connection, TRAINER_USERNAME, TRAINER_PASSWORD, "Workshop Trainer", "TRAINER");
    }

    private void seedUser(Connection connection, String username, String password, String displayName, String role) throws Exception {
        String sql = "INSERT OR IGNORE INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            statement.setString(2, passwordHasher.hash(password));
            statement.setString(3, displayName);
            statement.setString(4, role);
            statement.executeUpdate();
        }
    }

    private void migratePlaintextPasswords(Connection connection) throws Exception {
        List<StoredCredential> plaintextCredentials = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement("SELECT username, password FROM legacy_users");
             ResultSet result = statement.executeQuery()) {
            while (result.next()) {
                String storedPassword = result.getString("password");
                if (!passwordHasher.isEncoded(storedPassword)) {
                    plaintextCredentials.add(new StoredCredential(result.getString("username"), storedPassword));
                }
            }
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "UPDATE legacy_users SET password=? WHERE username=?")) {
            for (StoredCredential credential : plaintextCredentials) {
                statement.setString(1, passwordHasher.hash(credential.password()));
                statement.setString(2, credential.username());
                statement.executeUpdate();
            }
        }
    }

    public UserRecord findByCredentials(String username, String password) {
        String sql = "SELECT id, username, password, display_name, role FROM legacy_users WHERE username=?";
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next() || !passwordHasher.verify(password, result.getString("password"))) {
                    return null;
                }

                return new UserRecord(result.getLong("id"), result.getString("username"), result.getString("display_name"), result.getString("role"));
            }
        } catch (Exception error) {
            error.printStackTrace();
        }
        return null;
    }

    private record StoredCredential(String username, String password) {}
}
