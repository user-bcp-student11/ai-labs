package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

@ApplicationScoped
public class PasswordHasher {
    private static final String FORMAT = "pbkdf2-sha256";
    private static final String ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final int ITERATION_COUNT = 600_000;
    private static final int SALT_LENGTH_BYTES = 16;
    private static final int KEY_LENGTH_BITS = 256;
    private static final int HASH_COMPONENT_COUNT = 4;
    private static final int FORMAT_INDEX = 0;
    private static final int ITERATION_INDEX = 1;
    private static final int SALT_INDEX = 2;
    private static final int HASH_INDEX = 3;
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    public String hash(String password) {
        byte[] salt = new byte[SALT_LENGTH_BYTES];
        SECURE_RANDOM.nextBytes(salt);
        byte[] derivedKey = deriveKey(password, salt, ITERATION_COUNT);

        return String.join("$",
                FORMAT,
                Integer.toString(ITERATION_COUNT),
                Base64.getEncoder().encodeToString(salt),
                Base64.getEncoder().encodeToString(derivedKey));
    }

    public boolean verify(String password, String encodedPassword) {
        HashComponents components = parse(encodedPassword);
        if (components == null) {
            return false;
        }

        byte[] candidateKey = deriveKey(password, components.salt(), components.iterations());
        return MessageDigest.isEqual(components.derivedKey(), candidateKey);
    }

    boolean isEncoded(String value) {
        return parse(value) != null;
    }

    private HashComponents parse(String encodedPassword) {
        if (encodedPassword == null) {
            return null;
        }

        String[] components = encodedPassword.split("\\$", -1);
        if (components.length != HASH_COMPONENT_COUNT || !FORMAT.equals(components[FORMAT_INDEX])) {
            return null;
        }

        try {
            int iterations = Integer.parseInt(components[ITERATION_INDEX]);
            if (iterations != ITERATION_COUNT) {
                return null;
            }

            return new HashComponents(
                    iterations,
                    Base64.getDecoder().decode(components[SALT_INDEX]),
                    Base64.getDecoder().decode(components[HASH_INDEX]));
        } catch (IllegalArgumentException error) {
            return null;
        }
    }

    private byte[] deriveKey(String password, byte[] salt, int iterations) {
        PBEKeySpec keySpec = new PBEKeySpec(password.toCharArray(), salt, iterations, KEY_LENGTH_BITS);
        try {
            SecretKeyFactory keyFactory = SecretKeyFactory.getInstance(ALGORITHM);
            return keyFactory.generateSecret(keySpec).getEncoded();
        } catch (GeneralSecurityException error) {
            throw new IllegalStateException("Unable to derive password hash", error);
        } finally {
            keySpec.clearPassword();
        }
    }

    private record HashComponents(int iterations, byte[] salt, byte[] derivedKey) {}
}