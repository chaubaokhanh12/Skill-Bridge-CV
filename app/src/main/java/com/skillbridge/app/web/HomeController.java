package com.skillbridge.app.web;

import com.skillbridge.app.core.CoreClient;
import com.skillbridge.app.core.CoreException;
import com.skillbridge.app.core.Dtos;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Luồng người dùng sau bản vá (Phần D):
 *  GET  /                -> form (role + level + giờ + upload). Nếu đã xác nhận kỹ năng -> hiện kết quả.
 *  POST /scan            -> lưu CV/role/level, gọi /scan-cv, hiện bước XÁC NHẬN kỹ năng.
 *  POST /confirm-skills  -> gói confirmed_skills, lưu session, về / (ra kết quả).
 *  POST /confirm         -> nút xác nhận skill mơ hồ (override) -> gọi lại /analyze.
 *  POST /roadmap         -> lộ trình học (kèm level).
 *  POST /suggest         -> bước gợi ý viết lại CV (/cv-suggestions).
 *  POST /download-cv     -> tải CV gợi ý (/cv-export).
 *  POST /reset           -> làm lại từ đầu.
 */
@Controller
public class HomeController {

    private static final List<String> PROFS = List.of("proficient", "basic", "none");

    private final CoreClient core;
    private final UserSession session;

    public HomeController(CoreClient core, UserSession session) {
        this.core = core;
        this.session = session;
    }

    private static String esc(String s) {
        return s == null ? "" : s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private String overridesJson() {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (var e : session.getOverrides().entrySet()) {
            if (!first) {
                sb.append(",");
            }
            sb.append("\"").append(esc(e.getKey())).append("\":\"").append(esc(e.getValue())).append("\"");
            first = false;
        }
        return sb.append("}").toString();
    }

    private void addFormAttrs(Model model) {
        model.addAttribute("roles", core.roles().roles());
        model.addAttribute("selectedRole", session.getRoleId());
        model.addAttribute("level", session.getLevel());
        model.addAttribute("hours", session.getHours());
    }

    // ---------------- Trang chủ / kết quả ----------------
    @GetMapping("/")
    public String home(Model model) {
        addFormAttrs(model);
        if (session.hasCv() && session.isConfirmed()) {
            Dtos.AnalyzeResponse analysis = core.analyze(
                    session.getCvBytes(), session.getFilename(), session.getRoleId(),
                    overridesJson(), session.getLevel(), session.getConfirmedSkillsJson());
            model.addAttribute("analysis", analysis);
            model.addAttribute("filename", session.getFilename());
            List<String> highPriority = new ArrayList<>();
            for (Dtos.Skill s : analysis.skills()) {
                if ("Ưu tiên cao".equals(s.label())) {
                    highPriority.add(s.skillId());
                }
            }
            model.addAttribute("highPriorityIds", highPriority);
        }
        return "index";
    }

    // ---------------- Bước 1: quét CV -> xác nhận kỹ năng ----------------
    @PostMapping("/scan")
    public String scan(@RequestParam("cv_file") MultipartFile cvFile,
                       @RequestParam("role_id") String roleId,
                       @RequestParam(name = "level", defaultValue = "junior") String level,
                       @RequestParam(name = "hours", defaultValue = "5") int hours,
                       Model model) throws Exception {
        if (cvFile == null || cvFile.isEmpty()) {
            throw new CoreException("EMPTY_CV", "Bạn chưa chọn file CV. Vui lòng tải lên CV (.pdf, .docx hoặc .txt).");
        }
        session.startNewCv(cvFile.getBytes(), cvFile.getOriginalFilename(), roleId, level, hours);
        Dtos.ScanCvResponse scan = core.scanCv(session.getCvBytes(), session.getFilename());
        model.addAttribute("cvSkills", scan.cvSkills());
        model.addAttribute("roleId", roleId);
        model.addAttribute("level", level);
        model.addAttribute("filename", session.getFilename());
        return "confirm";
    }

    @PostMapping("/confirm-skills")
    public String confirmSkills(@RequestParam Map<String, String> params,
                                @RequestParam(name = "added", required = false) String added) {
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (var e : params.entrySet()) {
            if (!e.getKey().startsWith("prof_")) {
                continue;
            }
            String sid = e.getKey().substring(5);
            String prof = e.getValue();
            if (!PROFS.contains(prof)) {
                continue;
            }
            if (!first) {
                sb.append(",");
            }
            sb.append("{\"skill_id\":\"").append(esc(sid)).append("\",\"proficiency\":\"").append(prof).append("\"}");
            first = false;
        }
        if (added != null) {
            for (String a : added.split(",")) {
                String s = a.trim();
                if (s.isEmpty()) {
                    continue;
                }
                if (!first) {
                    sb.append(",");
                }
                sb.append("{\"skill_id\":\"").append(esc(s)).append("\",\"proficiency\":\"proficient\"}");
                first = false;
            }
        }
        session.setConfirmedSkillsJson(sb.append("]").toString());
        return "redirect:/";
    }

    // ---------------- Nút xác nhận skill mơ hồ (giữ nguyên) ----------------
    @PostMapping("/confirm")
    public String confirm(@RequestParam("skill_id") String skillId,
                          @RequestParam("value") String value) {
        session.putOverride(skillId, value);
        return "redirect:/";
    }

    // ---------------- Lộ trình học ----------------
    /**
     * Chỉ lưu lựa chọn + render khung trang. Dữ liệu lộ trình (meta/week/capstone/tips)
     * do JS phía roadmap.html tự lấy qua EventSource('/roadmap/stream?...') để hiện dần
     * từng tuần thay vì đợi core xử lý xong hết mới thấy gì (xem roadmapStream()).
     */
    @PostMapping("/roadmap")
    public String roadmap(@RequestParam(name = "skill_ids", required = false) List<String> skillIds,
                          @RequestParam(name = "hours", defaultValue = "5") int hours,
                          Model model) {
        session.setHours(hours);
        if (skillIds == null || skillIds.isEmpty()) {
            model.addAttribute("roadmapError", "Hãy chọn ít nhất một kỹ năng để tạo lộ trình.");
            return home(model);
        }
        model.addAttribute("skillIds", skillIds);
        model.addAttribute("hours", hours);
        return "roadmap";
    }

    /** SSE proxy sang core /roadmap/stream — browser EventSource chỉ GET nên Java đứng giữa POST hộ. */
    @GetMapping(value = "/roadmap/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> roadmapStream(
            @RequestParam(name = "skill_ids") List<String> skillIds,
            @RequestParam(name = "hours", defaultValue = "5") int hours) {
        return core.roadmapStream(session.getRoleId(), session.getLevel(), hours, skillIds)
                .map(data -> ServerSentEvent.builder(data).build())
                .onErrorResume(ex -> Flux.just(ServerSentEvent.builder(
                        "{\"type\":\"error\",\"data\":{\"code\":\"STREAM_FAILED\",\"message\":\""
                                + esc(ex.getMessage()) + "\"}}").build()));
    }

    // ---------------- Bước cuối: gợi ý viết lại CV ----------------
    @PostMapping("/suggest")
    public String suggest(Model model) {
        if (!session.hasCv()) {
            throw new CoreException("NO_CV", "Chưa có CV để gợi ý. Hãy phân tích một CV trước.");
        }
        Dtos.CvSuggestionsResponse res = core.cvSuggestions(
                session.getCvBytes(), session.getFilename(), session.getRoleId(), session.getLevel());
        model.addAttribute("suggestions", res.suggestions());
        model.addAttribute("note", res.note());
        model.addAttribute("filename", session.getFilename());
        return "cv-suggest";
    }

    @PostMapping("/download-cv")
    public ResponseEntity<byte[]> downloadCv(
            @RequestParam(name = "suggested", required = false) List<String> suggested) {
        List<Map<String, String>> accepted = new ArrayList<>();
        if (suggested != null) {
            for (String s : suggested) {
                accepted.add(Map.of("suggested", s));
            }
        }
        byte[] md = core.cvExport(accepted, "md");
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=cv_goi_y.md")
                .contentType(MediaType.parseMediaType("text/markdown"))
                .body(md);
    }

    @PostMapping("/reset")
    public String reset() {
        session.reset();
        return "redirect:/";
    }

    /** Lỗi từ core (hoặc thiếu file) -> banner thân thiện, không crash. */
    @ExceptionHandler(CoreException.class)
    public String handleCoreError(CoreException ex, Model model) {
        model.addAttribute("error", ex.getMessage());
        safeFormAttrs(model);
        return "index";
    }

    /** Core không phản hồi / timeout / không kết nối được -> banner, không Whitelabel. */
    @ExceptionHandler(org.springframework.web.client.ResourceAccessException.class)
    public String handleCoreUnreachable(Exception ex, Model model) {
        model.addAttribute("error",
                "Không gọi được service AI (core) — core chưa chạy hoặc xử lý quá lâu. "
                + "Hãy chắc core đang chạy ở cổng 8000 rồi thử lại.");
        safeFormAttrs(model);
        return "index";
    }

    /** Lưới cuối: bất kỳ lỗi nào khác cũng ra banner thay vì trang lỗi trắng. */
    @ExceptionHandler(Exception.class)
    public String handleUnexpected(Exception ex, Model model) {
        model.addAttribute("error", "Đã xảy ra lỗi không mong muốn: " + ex.getMessage());
        safeFormAttrs(model);
        return "index";
    }

    /** Nạp lại attr cho form; nếu chính core cũng lỗi thì để danh sách role rỗng. */
    private void safeFormAttrs(Model model) {
        try {
            addFormAttrs(model);
        } catch (Exception ignore) {
            model.addAttribute("roles", Collections.emptyList());
        }
    }
}
