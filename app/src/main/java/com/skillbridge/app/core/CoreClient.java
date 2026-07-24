package com.skillbridge.app.core;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

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
    private final WebClient webClient;

    public CoreClient(RestClient.Builder builder, WebClient.Builder webClientBuilder,
                      @Value("${core.base-url}") String baseUrl) {
        // Client JDK (khong dung Reactor Netty) + timeout rong: /scan-cv va /analyze co the
        // chay pipeline LLM/embedding mat nhieu giay, khong duoc cat som (tranh ReadTimeout).
        SimpleClientHttpRequestFactory rf = new SimpleClientHttpRequestFactory();
        rf.setConnectTimeout(10_000);    // 10s de ket noi
        rf.setReadTimeout(180_000);      // 180s cho core xu ly xong
        this.http = builder
                .baseUrl(baseUrl)
                .requestFactory(rf)
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
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
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

    /**
     * POST /roadmap/stream (SSE) — moi phan tu la 1 dong JSON tho ({"type":..,"data":..}),
     * cung shape voi cac event cua core (xem main.py _sse_event). Khong deserialize o day,
     * de HomeController forward nguyen van cho browser tu parse.
     */
    public Flux<String> roadmapStream(String roleId, String level, int hoursPerWeek, List<String> skillIds) {
        Map<String, Object> req = Map.of(
                "role_id", roleId,
                "level", level == null ? "junior" : level,
                "hours_per_week", hoursPerWeek,
                "skill_ids", skillIds);
        return webClient.post().uri("/roadmap/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(req)
                .retrieve()
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() { })
                .mapNotNull(ServerSentEvent::data);
    }
}
