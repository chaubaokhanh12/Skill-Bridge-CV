package com.skillbridge.app.core;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * DTO khop API contract (Muc 1 cua CORE_AI_Python_Spec).
 * JSON core dung snake_case; da bat spring.jackson.property-naming-strategy=SNAKE_CASE
 * nen field camelCase o day tu map (skill_id -> skillId, gap_score -> gapScore, ...).
 */
public final class Dtos {

    private Dtos() {
    }

    // ---- GET /roles ----
    public record Role(String id, String name, @JsonProperty("jd_count") Integer jdCount) {
    }

    public record RolesResponse(List<Role> roles) {
    }

    // ---- POST /scan-cv ----
    public record CvSkill(
            @JsonProperty("skill_id") String skillId,
            String name,
            @JsonProperty("proficiency_guess") String proficiencyGuess,
            String evidence) {
    }

    public record ScanCvResponse(@JsonProperty("cv_skills") List<CvSkill> cvSkills) {
    }

    // ---- POST /cv-suggestions ----
    public record Suggestion(String original, String suggested, String reason) {
    }

    public record CvSuggestionsResponse(List<Suggestion> suggestions) {
    }

    // ---- POST /analyze ----
    public record RoleRef(String id, String name, String level) {
    }

    public record Readiness(String band, String core, @JsonProperty("jd_count") Integer jdCount) {
    }

    public record Demand(
            @JsonProperty("jd_count") Integer jdCount,
            @JsonProperty("total_jd") Integer totalJd,
            @JsonProperty("required_count") Integer requiredCount,
            Double freq) {
        /** freq (0..1) sang phan tram nguyen de ve thanh bar, khong in so thap phan. */
        public int freqPercent() {
            return freq == null ? 0 : (int) Math.round(freq * 100);
        }
    }

    public record Coverage(@JsonProperty("in_cv") Boolean inCv, String evidence) {
    }

    public record Skill(
            @JsonProperty("skill_id") String skillId,
            String name,
            String category,
            String status,
            String label,
            @JsonProperty("gap_score") Double gapScore,
            Demand demand,
            Coverage coverage,
            @JsonProperty("needs_confirmation") Boolean needsConfirmation) {

        /** Class mau cho badge nhan (dung trong CSS). */
        public String labelClass() {
            if (label == null) {
                return "gray";
            }
            return switch (label) {
                case "Ưu tiên cao" -> "high";
                case "Cần xác nhận" -> "confirm";
                case "Đã đáp ứng" -> "met";
                default -> "gray";
            };
        }

        /** Mo ta trang thai CV cho dong bang chung (Muc 5.2). */
        public String cvStatusText() {
            if (coverage == null || coverage.inCv() == null || !coverage.inCv()) {
                return "không tìm thấy trong CV";
            }
            if ("partial".equals(status)) {
                return "có nhắc nhưng không rõ mức độ";
            }
            return "có trong CV";
        }
    }

    public record AnalyzeResponse(RoleRef role, Readiness readiness, List<Skill> skills) {
    }

    // ---- POST /roadmap ----
    public record Resource(String title, String url, Integer hours) {
    }

    public record MiniProject(
            String title,
            String goal,
            String difficulty,
            String dataset,
            @JsonProperty("done_criteria") List<String> doneCriteria,
            List<String> deliverables,
            String stretch,
            @JsonProperty("cv_bullet") String cvBullet) {
    }

    public record Week(
            Integer week,
            String skill,
            @JsonProperty("skill_id") String skillId,
            String phase,
            String level,
            String focus,
            String why,
            List<String> objectives,
            @JsonProperty("estimated_hours") Integer estimatedHours,
            List<Resource> resources,
            List<String> practice,
            String checkpoint,
            @JsonProperty("mini_project") MiniProject miniProject) {
    }

    public record RoadmapMeta(
            @JsonProperty("total_weeks") Integer totalWeeks,
            @JsonProperty("hours_per_week") Integer hoursPerWeek,
            @JsonProperty("total_hours") Integer totalHours,
            @JsonProperty("skill_count") Integer skillCount,
            String summary) {
    }

    public record Capstone(
            String title,
            String goal,
            @JsonProperty("skills_used") List<String> skillsUsed,
            @JsonProperty("done_criteria") List<String> doneCriteria,
            @JsonProperty("cv_bullet") String cvBullet) {
    }

    public record RoadmapResponse(
            RoadmapMeta meta,
            List<Week> weeks,
            Capstone capstone,
            @JsonProperty("portfolio_tips") List<String> portfolioTips) {
    }

    // ---- Loi chung: { "code": "...", "message": "..." } ----
    public record CoreError(String code, String message) {
    }
}
