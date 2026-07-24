"""service.py — AnalysisService: điều phối toàn bộ pipeline cho tầng API.

Gom Taxonomy + Extractor + MarketAnalyzer + RoadmapBuilder + CvSuggester lại một chỗ,
phơi ra các thao tác nghiệp vụ (roles/scan/analyze/roadmap/suggest/export). main.py chỉ
map HTTP ↔ các phương thức này, không chứa logic.
"""
import glob
import json

from . import config
from .errors import AppError
from .taxonomy import get_taxonomy
from .extract import get_extractor, read_cv, scan_cv
from .analyze import MarketAnalyzer
from .roadmap import RoadmapBuilder
from .cv_suggest import CvSuggester


class AnalysisService:
    def __init__(self):
        with open(config.ROLES_PATH, encoding="utf-8") as f:
            self.roles_cfg = json.load(f)
        self.tax = get_taxonomy()
        self.extractor = get_extractor(self.tax)
        self.analyzer = MarketAnalyzer(self.tax)
        self.roadmap_builder = RoadmapBuilder(self.tax)
        self.suggester = CvSuggester(self.tax)

    # -- roles -------------------------------------------------------------
    def _jd_files(self, role: dict) -> list:
        return sorted(glob.glob(config.path(role["jds_dir"], "*.txt")))

    def roles(self) -> list:
        return [{"id": r["id"], "name": r["name"], "jd_count": len(self._jd_files(r))}
                for r in self.roles_cfg]

    def get_role(self, role_id: str) -> dict:
        for r in self.roles_cfg:
            if r["id"] == role_id:
                return r
        raise AppError("ROLE_NOT_FOUND", f"Không tìm thấy role_id: {role_id}")

    # -- cầu thị trường từ JD của role -------------------------------------
    def _market(self, role: dict):
        files = self._jd_files(role)
        if not files:
            raise AppError("NO_JDS", f"Role '{role['id']}' chưa có JD nào trong {role['jds_dir']}")
        lists = []
        for fp in files:
            with open(fp, encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            norm = []
            for it in self.extractor.extract_jd_skills(txt):
                sid, _ = self.tax.normalize(it.get("name", ""))
                if sid:
                    norm.append({"skill_id": sid, "importance": it.get("importance", "preferred")})
            lists.append(norm)
        return len(files), lists

    # -- /scan-cv ----------------------------------------------------------
    def scan(self, cv_path: str) -> dict:
        return {"cv_skills": scan_cv(read_cv(cv_path), self.extractor, self.tax)}

    # -- /analyze ----------------------------------------------------------
    def analyze(self, cv_path: str, role_id: str, overrides: dict = None,
                level: str = "junior", confirmed: list = None) -> dict:
        role = self.get_role(role_id)
        overrides = overrides or {}
        total_jd, jd_lists = self._market(role)
        profile = self.analyzer.market_profile(jd_lists, total_jd)

        cv_map = {}
        if confirmed:  # hồ sơ user xác nhận -> dùng thẳng, bỏ trích từ file
            for it in confirmed:
                sid, prof = it.get("skill_id"), it.get("proficiency")
                if sid and prof in ("proficient", "basic"):
                    cv_map[sid] = {"proficiency": prof, "evidence": None}
        else:  # trích từ CV như cũ
            for it in self.extractor.extract_cv_skills(read_cv(cv_path)):
                sid, conf = self.tax.normalize(it.get("name", ""))
                if not sid:
                    continue
                if sid not in cv_map or conf > cv_map[sid].get("conf", 0):
                    cv_map[sid] = {"evidence": it.get("evidence") or None, "conf": conf}

        coverage = self.analyzer.resolve_coverage(profile, cv_map, overrides, level)
        return self.analyzer.build_analysis(role, profile, coverage, total_jd, level)

    # -- /roadmap ----------------------------------------------------------
    def roadmap(self, role_id: str, level: str, hours_per_week: int, skill_ids: list) -> dict:
        role = self.get_role(role_id)
        demand, n_jd = None, None
        try:  # nối 'vì sao học' với cầu JD thật (JD extraction đã cache từ /analyze)
            n_jd, jd_lists = self._market(role)
            demand = self.analyzer.market_profile(jd_lists, n_jd)
        except Exception:  # noqa: BLE001 - thiếu demand thì roadmap vẫn chạy
            demand, n_jd = None, None
        return self.roadmap_builder.build(skill_ids, hours_per_week, demand=demand,
                                          role_name=role["name"], total_jd=n_jd, level=level)

    def roadmap_stream(self, role_id: str, level: str, hours_per_week: int, skill_ids: list):
        """Như roadmap() nhưng generator — mỗi tuần yield ngay khi tính xong (xem
        RoadmapBuilder.build_stream)."""
        role = self.get_role(role_id)
        demand, n_jd = None, None
        try:
            n_jd, jd_lists = self._market(role)
            demand = self.analyzer.market_profile(jd_lists, n_jd)
        except Exception:  # noqa: BLE001 - thiếu demand thì roadmap vẫn chạy
            demand, n_jd = None, None
        yield from self.roadmap_builder.build_stream(
            skill_ids, hours_per_week, demand=demand, role_name=role["name"],
            total_jd=n_jd, level=level)

    # -- /cv-suggestions + /cv-export --------------------------------------
    def suggestions(self, cv_path: str, role_id: str, level: str) -> dict:
        role = self.get_role(role_id)
        return {"suggestions": self.suggester.suggest(read_cv(cv_path), role["name"], level)}

    def export_cv(self, accepted: list) -> str:
        return self.suggester.export_markdown(accepted or [])
