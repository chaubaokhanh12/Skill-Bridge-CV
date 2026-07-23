"""extract.py — Tầng 2: đọc CV + trích skill từ CV/JD.

- read_cv(path): .pdf / .docx / .txt -> text (import đọc file lười).
- SkillExtractor: giao diện trích skill; hai hiện thực có thể HOÁN ĐỔI:
    * LLMExtractor  — dùng LLM (Claude/Groq/... qua llm.complete_json), ép JSON, temperature=0.
    * RuleExtractor — bộ trích offline theo alias (TEST DOUBLE, không gọi API).
- scan_cv(): trích + normalize + đoán proficiency cho bước xác nhận (/scan-cv).

Việc extractor hoán đổi được là bằng chứng: "trí tuệ" của kết quả nằm ở tầng chuẩn hóa +
chấm điểm phía sau, KHÔNG phụ thuộc riêng LLM (xem TECHNICAL_REPORT.md).
"""
import os
import re
from abc import ABC, abstractmethod

from . import config, llm
from .taxonomy import Taxonomy


# --------------------------------------------------------------------------- #
# Đọc CV
# --------------------------------------------------------------------------- #
def read_cv(path: str) -> str:
    p = path.lower()
    if p.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    if p.endswith(".docx"):
        import docx
        return "\n".join(par.text for par in docx.Document(path).paragraphs)
    if p.endswith(".txt"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    ext = os.path.splitext(path)[1] or "(không rõ)"
    raise ValueError(f"Định dạng CV không hỗ trợ: {ext}. Chỉ nhận .pdf, .docx, .txt")


# --------------------------------------------------------------------------- #
# Prompt (ép JSON theo schema spec)
# --------------------------------------------------------------------------- #
JD_PROMPT = """Bạn là chuyên gia phân tích tin tuyển dụng (Job Description).
Đọc JD dưới đây và trích XUẤT MỌI kỹ năng chuyên môn được nhắc tới.
Với mỗi kỹ năng, gán importance dựa trên từ khóa trong JD:
- "required": bắt buộc — "must", "bắt buộc", "yêu cầu", "thành thạo", "required".
- "preferred": ưu tiên — "ưu tiên", "preferred", "nên có", "plus".
- "nice_to_have": lợi thế — "là lợi thế", "nice to have", "a plus", "bonus".
Không rõ tín hiệu -> mặc định "preferred".
CHỈ trả JSON hợp lệ, KHÔNG giải thích, KHÔNG markdown:
{{"skills":[{{"name":"<tên kỹ năng>","importance":"required|preferred|nice_to_have"}}]}}

JD:
\"\"\"
{jd}
\"\"\""""

CV_PROMPT = """Bạn là chuyên gia đọc CV/hồ sơ ứng viên.
Trích XUẤT các kỹ năng chuyên môn CÓ BẰNG CHỨNG RÕ RÀNG trong CV.

QUY TẮC TUYỆT ĐỐI — CẤM SUY DIỄN:
- CHỈ trích kỹ năng được nêu tên trực tiếp hoặc chứng minh bằng mô tả công việc/dự án.
- KHÔNG suy đoán từ chức danh, ngành học, hay công cụ liên quan.
- CV không nhắc tới -> TUYỆT ĐỐI không thêm.

Với mỗi kỹ năng: "evidence" trích dẫn ngắn từ CV; "years" số năm nếu suy ra được (không rõ ghi 0).
CHỈ trả JSON hợp lệ, KHÔNG giải thích, KHÔNG markdown:
{{"skills":[{{"name":"<tên>","evidence":"<trích dẫn>","years":<số>}}]}}

CV:
\"\"\"
{cv}
\"\"\""""


# --------------------------------------------------------------------------- #
# Giao diện + hai hiện thực
# --------------------------------------------------------------------------- #
class SkillExtractor(ABC):
    @abstractmethod
    def extract_jd_skills(self, jd: str) -> list:
        ...

    @abstractmethod
    def extract_cv_skills(self, cv: str) -> list:
        ...


class LLMExtractor(SkillExtractor):
    """Trích skill bằng LLM (provider bất kỳ), ép JSON, có cache."""

    def extract_jd_skills(self, jd: str) -> list:
        return llm.complete_json(JD_PROMPT.format(jd=jd)).get("skills", [])

    def extract_cv_skills(self, cv: str) -> list:
        return llm.complete_json(CV_PROMPT.format(cv=cv)).get("skills", [])


class RuleExtractor(SkillExtractor):
    """Bộ trích offline theo alias trong taxonomy (TEST DOUBLE, không gọi API)."""

    def __init__(self, taxonomy: Taxonomy):
        self.tax = taxonomy
        self.aliases = [
            (s["skill_id"], s["canonical_name"], a.lower())
            for s in taxonomy.skills
            for a in [s["canonical_name"], *s.get("aliases", [])]
        ]

    @staticmethod
    def _alias_in(low_text: str, alias: str) -> bool:
        if not alias:
            return False
        # alias là 1 từ chữ-số -> ranh giới từ (tránh 'excel' dính 'excellent',
        # 'looker' dính 'onlooker'...). Alias nhiều từ/ký tự đặc biệt -> khớp chuỗi con.
        if re.fullmatch(r"[a-z0-9]+", alias):
            return re.search(r"\b" + re.escape(alias) + r"\b", low_text) is not None
        return alias in low_text

    def extract_jd_skills(self, jd: str) -> list:
        section = "preferred"
        seen = {}
        for line in jd.splitlines():
            low = line.lower()
            if any(w in low for w in ["bắt buộc", "yêu cầu", "must", "required", "requirement"]):
                section = "required"
            elif any(w in low for w in ["là lợi thế", "lợi thế", "nice to have", "bonus", "a plus"]):
                section = "nice_to_have"
            elif any(w in low for w in ["ưu tiên", "preferred", "nên có"]):
                section = "preferred"
            for sid, canon, alias in self.aliases:
                if sid in seen:
                    continue
                if self._alias_in(low, alias):
                    imp = section
                    if any(w in low for w in ["bắt buộc", "must have", "must ", "required"]):
                        imp = "required"
                    elif any(w in low for w in ["là lợi thế", "nice to have", "a plus", "bonus"]):
                        imp = "nice_to_have"
                    seen[sid] = {"name": canon, "importance": imp}
        return list(seen.values())

    def extract_cv_skills(self, cv: str) -> list:
        lines = cv.splitlines()
        out, seen = [], set()
        for sid, canon, alias in self.aliases:
            if sid in seen:
                continue
            for line in lines:
                if self._alias_in(line.lower(), alias):
                    seen.add(sid)
                    out.append({"name": canon, "evidence": line.strip()[:200],
                                "years": _parse_years(line)})
                    break
        return out


def _parse_years(line: str) -> float:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:\+)?\s*(năm|years?|yrs?)", line.lower())
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return 0
    return 0


def get_extractor(taxonomy: Taxonomy) -> SkillExtractor:
    """Chọn extractor theo cấu hình: OFFLINE_LLM=1 -> RuleExtractor, ngược lại LLMExtractor."""
    return RuleExtractor(taxonomy) if config.OFFLINE_LLM else LLMExtractor()


# --------------------------------------------------------------------------- #
# scan_cv — cho bước xác nhận kỹ năng (/scan-cv)
# --------------------------------------------------------------------------- #
_PROF_RANK = {"unknown": 0, "basic": 1, "proficient": 2}


def _prof_guess(years, evidence) -> str:
    try:
        y = float(years or 0)
    except (TypeError, ValueError):
        y = 0
    if y >= 2:
        return "proficient"
    if y >= 1 or (evidence and str(evidence).strip()):
        return "basic"
    return "unknown"


def scan_cv(cv_text: str, extractor: SkillExtractor, taxonomy: Taxonomy) -> list:
    """Trích + normalize + đoán proficiency (proficient|basic|unknown). Giữ nguyên tắc
    'cấm suy diễn' — chỉ lấy skill có bằng chứng."""
    seen = {}
    for it in extractor.extract_cv_skills(cv_text):
        sid, _conf = taxonomy.normalize(it.get("name", ""))
        if not sid:
            continue
        prof = _prof_guess(it.get("years"), it.get("evidence"))
        if sid in seen and _PROF_RANK[prof] <= _PROF_RANK[seen[sid]["proficiency_guess"]]:
            continue
        seen[sid] = {
            "skill_id": sid,
            "name": taxonomy.canonical_name(sid),
            "proficiency_guess": prof,
            "evidence": it.get("evidence") or None,
        }
    return list(seen.values())
