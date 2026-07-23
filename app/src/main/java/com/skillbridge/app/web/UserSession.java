package com.skillbridge.app.web;

import org.springframework.context.annotation.ScopedProxyMode;
import org.springframework.stereotype.Component;
import org.springframework.web.context.annotation.SessionScope;

import java.io.Serializable;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Giu state theo phien (Muc 6): CV da upload + role + gio/tuan + overrides.
 * Nho vay khi user bam nut xac nhan skill, khong phai upload lai file.
 */
@Component
@SessionScope(proxyMode = ScopedProxyMode.TARGET_CLASS)
public class UserSession implements Serializable {

    private byte[] cvBytes;
    private String filename;
    private String roleId;
    private String level = "junior";
    private int hours = 5;
    private String confirmedSkillsJson;
    private final Map<String, String> overrides = new LinkedHashMap<>();

    public boolean hasCv() {
        return cvBytes != null && cvBytes.length > 0;
    }

    /** Đã qua bước xác nhận kỹ năng chưa (có thì mới hiện màn kết quả). */
    public boolean isConfirmed() {
        return confirmedSkillsJson != null && !confirmedSkillsJson.isBlank();
    }

    public void startNewCv(byte[] cvBytes, String filename, String roleId, String level, int hours) {
        this.cvBytes = cvBytes;
        this.filename = filename;
        this.roleId = roleId;
        this.level = level;
        this.hours = hours;
        this.confirmedSkillsJson = null;
        this.overrides.clear();
    }

    public void putOverride(String skillId, String value) {
        if (skillId != null && value != null) {
            overrides.put(skillId, value);
        }
    }

    public void reset() {
        cvBytes = null;
        filename = null;
        roleId = null;
        level = "junior";
        hours = 5;
        confirmedSkillsJson = null;
        overrides.clear();
    }

    public String getLevel() {
        return level;
    }

    public String getConfirmedSkillsJson() {
        return confirmedSkillsJson;
    }

    public void setConfirmedSkillsJson(String confirmedSkillsJson) {
        this.confirmedSkillsJson = confirmedSkillsJson;
    }

    public byte[] getCvBytes() {
        return cvBytes;
    }

    public String getFilename() {
        return filename;
    }

    public String getRoleId() {
        return roleId;
    }

    public int getHours() {
        return hours;
    }

    public void setHours(int hours) {
        this.hours = hours;
    }

    public Map<String, String> getOverrides() {
        return overrides;
    }
}
