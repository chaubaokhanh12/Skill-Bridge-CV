"""analyze.py — Tầng 4 (cầu thị trường) + Tầng 5 (gap + readiness).

MarketAnalyzer là lõi TẤT ĐỊNH của hệ thống — không gọi LLM, không ngẫu nhiên:
  demand    = freq × weight            (weight: required 1.0 / preferred 0.6 / nice 0.3)
  gap_score = demand × (1 − coverage)  (coverage: covered 1.0 / partial 0.5 / missing 0.0)
Nhãn theo 4 quy tắc; readiness ở dạng DẢI ("khoảng lo–hi%"), không bao giờ số thập phân.

Toàn bộ đây là Python thuần (chỉ cần Taxonomy để lấy tên/category) nên test được độc lập.
"""
from . import config
from .taxonomy import Taxonomy


class MarketAnalyzer:
    def __init__(self, taxonomy: Taxonomy):
        self.tax = taxonomy

    # -- Tầng 4: tổng hợp cầu thị trường từ nhiều JD ------------------------
    def market_profile(self, jd_skill_lists: list, total_jd: int) -> dict:
        """jd_skill_lists: list theo từng JD [{skill_id, importance}, ...] (đã normalize).
        Trả {skill_id: {jd_count, required_count, freq, weight, demand}}."""
        agg = {}
        for skills in jd_skill_lists:  # mỗi 'skills' = 1 JD
            strongest = {}
            for it in skills:
                sid, imp = it["skill_id"], it.get("importance", "preferred")
                w = config.IMPORTANCE_WEIGHT.get(imp, 0.6)
                if sid not in strongest or w > config.IMPORTANCE_WEIGHT.get(strongest[sid], 0.0):
                    strongest[sid] = imp  # trong 1 JD giữ importance mạnh nhất
            for sid, imp in strongest.items():
                a = agg.setdefault(sid, {"jd_count": 0, "required_count": 0, "weight_sum": 0.0})
                a["jd_count"] += 1
                a["weight_sum"] += config.IMPORTANCE_WEIGHT.get(imp, 0.6)
                if imp == "required":
                    a["required_count"] += 1

        profile = {}
        for sid, a in agg.items():
            freq = a["jd_count"] / total_jd if total_jd else 0.0
            weight = a["weight_sum"] / a["jd_count"] if a["jd_count"] else 0.0
            profile[sid] = {
                "jd_count": a["jd_count"], "required_count": a["required_count"],
                "freq": freq, "weight": weight, "demand": freq * weight,
            }
        return profile

    # -- coverage: CV/xác nhận + overrides + ngưỡng theo level -------------
    @staticmethod
    def proficiency_status(prof: str, level: str = "junior") -> str:
        """proficient->covered; basic->covered nếu junior, còn lại partial; none->missing; unknown->partial."""
        if prof == "proficient":
            return "covered"
        if prof == "basic":
            return "covered" if level == "junior" else "partial"
        if prof == "none":
            return "missing"
        return "partial"

    def resolve_coverage(self, profile: dict, cv_map: dict, override_map: dict, level: str = "junior") -> dict:
        """cv_map[sid] dạng {"proficiency":...} (xác nhận) hoặc {"conf":...} (trích CV kiểu cũ).
        override_map: {sid: have|partial|none}. Trả {sid: {status, in_cv, evidence}}."""
        cov = {}
        for sid in profile:
            entry = cv_map.get(sid)
            in_cv = entry is not None
            evidence = entry.get("evidence") if in_cv else None
            if sid in override_map:
                status = config.OVERRIDE_STATUS.get(override_map[sid], "missing")
            elif in_cv and "proficiency" in entry:
                status = self.proficiency_status(entry.get("proficiency", "unknown"), level)
            elif in_cv:
                conf = entry.get("conf", 1.0)
                status = "covered" if conf >= config.PARTIAL_CONF_MAX else "partial"
            else:
                status = "missing"
            cov[sid] = {"status": status, "in_cv": in_cv, "evidence": evidence}
        return cov

    # -- Tầng 5: gap + nhãn + readiness -----------------------------------
    @staticmethod
    def _label(status: str, freq: float, jd_count: int, low_cut: float) -> str:
        if status == "covered":
            return config.LABEL_MET
        if jd_count < low_cut:
            return config.LABEL_LOW
        if status == "missing" and freq >= config.CORE_FREQ:
            return config.LABEL_HIGH
        return config.LABEL_CONFIRM

    def gap_analysis(self, profile: dict, coverage_map: dict, total_jd: int) -> list:
        low_cut = max(3, 0.15 * total_jd)
        rows = []
        for sid, p in profile.items():
            cov = coverage_map.get(sid, {"status": "missing", "in_cv": False, "evidence": None})
            status = cov["status"]
            gap = p["demand"] * (1 - config.COVERAGE_VALUE[status])
            label = self._label(status, p["freq"], p["jd_count"], low_cut)
            rows.append({
                "skill_id": sid,
                "name": self.tax.canonical_name(sid),
                "category": self.tax.category(sid),
                "status": status,
                "label": label,
                "gap_score": round(gap, 2),
                "demand": {
                    "jd_count": p["jd_count"], "total_jd": total_jd,
                    "required_count": p["required_count"], "freq": round(p["freq"], 2),
                },
                "coverage": {"in_cv": bool(cov["in_cv"]), "evidence": cov["evidence"]},
                "needs_confirmation": label == config.LABEL_CONFIRM,
            })
        return rows

    @staticmethod
    def _band(ratio: float) -> str:
        pct = max(0, min(100, round(ratio * 100)))
        lo = min(90, (pct // 10) * 10)
        return f"khoảng {lo}–{lo + 10}%"  # '–' en-dash theo spec

    def readiness(self, rows: list, profile: dict, total_jd: int) -> dict:
        status_by_id = {r["skill_id"]: r["status"] for r in rows}
        num = den = 0.0
        for sid, p in profile.items():
            d = p["demand"]
            num += d * config.COVERAGE_VALUE[status_by_id.get(sid, "missing")]
            den += d
        ratio = num / den if den else 0.0
        core_ids = [sid for sid, p in profile.items() if p["freq"] >= config.CORE_FREQ]
        have = sum(1 for sid in core_ids if status_by_id.get(sid) == "covered")
        return {"band": self._band(ratio), "core": f"{have}/{len(core_ids)} skill core", "jd_count": total_jd}

    def build_analysis(self, role: dict, profile: dict, coverage_map: dict,
                       total_jd: int, level: str = None) -> dict:
        rows = self.gap_analysis(profile, coverage_map, total_jd)
        rows.sort(key=lambda r: (r["gap_score"], r["demand"]["freq"]), reverse=True)
        role_out = {"id": role["id"], "name": role["name"]}
        if level:
            role_out["level"] = level
        return {"role": role_out, "readiness": self.readiness(rows, profile, total_jd), "skills": rows}
