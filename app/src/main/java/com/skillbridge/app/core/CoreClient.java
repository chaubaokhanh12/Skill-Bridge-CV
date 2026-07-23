package com.skillbridge.app.core;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Client goi 3 endpoint cua service AI (Python core) theo API contract Muc 1.
 * Moi loi 4xx/5xx tu core (shape {code,message}) duoc chuyen thanh CoreException
 * de controller hien message than thien thay vi crash.
 */
@Service
public class CoreClient {

    private static final Pattern MSG = Pattern.compile("\"message\"\\s*:\\s*\"(.*?)\"");
    private static final Pattern CODE = Pattern.compile("\"code\"\\s*:\\s*\"(.*?)\"");

    private final RestClient http;

    public CoreClient(RestClient.Builder builder, @Value("${core.base-url}") String baseUrl) {
        this.http = builder
                .baseUrl(baseUrl)
                .defaultStatusHandler(status -> status.isError(), (request, response) -> {
                    String body = new String(response.getBody().readAllBytes(), StandardCharsets.UTF_8);
                    String message = extract(MSG, body);
                    String code = extract(CODE, body);
                    if (message == null) {
                        message = "Service AI dang khong phan hoi (" + response.getStatusCode().value() + ").";
                    }
                    throw new CoreException(code != null ? code : "CORE_ERROR", message);
                })
                .build();
    }

    private static String extract(Pattern p, String body) {
        Matcher m = p.matcher(body);
        return m.find() ? m.group(1) : null;
    }

    /** GET /roles */
    public Dtos.RolesResponse roles() {
        return http.get().uri("/roles").retrieve().body(Dtos.RolesResponse.class);
    }

    private static ByteArrayResource filePart(byte[] cv, String filename) {
        return new ByteArrayResource(cv) {
            @Override
            public String getFilename() {
                return filename;
            }
        };
    }

    /** POST /scan-cv (multipart: cv_file) -> danh sách skill để user xác nhận. */
    public Dtos.ScanCvResponse scanCv(byte[] cv, String filename) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("cv_file", filePart(cv, filename));
        return http.post().uri("/scan-cv")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(b.build())
                .retrieve()
                .body(Dtos.ScanCvResponse.class);
    }

    /** POST /analyze (multipart: cv_file, role_id, overrides, level, confirmed_skills). */
    public Dtos.AnalyzeResponse analyze(byte[] cv, String filename, String roleId,
                                        String overridesJson, String level, String confirmedSkillsJson) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("cv_file", filePart(cv, filename));
        b.part("role_id", roleId);
        b.part("overrides", overridesJson == null ? "{}" : overridesJson);
        b.part("level", level == null ? "junior" : level);
        if (confirmedSkillsJson != null && !confirmedSkillsJson.isBlank()) {
            b.part("confirmed_skills", confirmedSkillsJson);
        }
        return http.post().uri("/analyze")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(b.build())
                .retrieve()
                .body(Dtos.AnalyzeResponse.class);
    }

    /** POST /cv-suggestions (multipart: cv_file, role_id, level). */
    public Dtos.CvSuggestionsResponse cvSuggestions(byte[] cv, String filename, String roleId, String level) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("cv_file", filePart(cv, filename));
        b.part("role_id", roleId);
        b.part("level", level == null ? "junior" : level);
        return http.post().uri("/cv-suggestions")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(b.build())
                .retrieve()
                .body(Dtos.CvSuggestionsResponse.class);
    }

    /** POST /cv-export (json: accepted[], format) -> nội dung file CV để tải. */
    public byte[] cvExport(List<Map<String, String>> accepted, String format) {
        Map<String, Object> req = Map.of("accepted", accepted, "format", format);
        return http.post().uri("/cv-export")
                .contentType(MediaType.APPLICATION_JSON)
                .body(req)
                .retrieve()
                .body(byte[].class);
    }

    /** POST /roadmap (json: role_id, level, hours_per_week, skill_ids). */
    public Dtos.RoadmapResponse roadmap(String roleId, String level, int hoursPerWeek, List<String> skillIds) {
        Map<String, Object> req = Map.of(
                "role_id", roleId,
                "level", level == null ? "junior" : level,
                "hours_per_week", hoursPerWeek,
                "skill_ids", skillIds);
        return http.post().uri("/roadmap")
                .contentType(MediaType.APPLICATION_JSON)
                .body(req)
                .retrieve()
                .body(Dtos.RoadmapResponse.class);
    }
}
