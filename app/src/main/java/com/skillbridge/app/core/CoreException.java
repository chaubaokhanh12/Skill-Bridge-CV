package com.skillbridge.app.core;

/** Loi khi goi service AI (core). message da than thien de hien thang ra UI. */
public class CoreException extends RuntimeException {

    private final String code;

    public CoreException(String code, String message) {
        super(message);
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}
