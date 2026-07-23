"""cv_suggest.py — Gợi ý VIẾT LẠI CV cho khớp ngôn ngữ JD.

RÀNG BUỘC CỨNG: chỉ DIỄN ĐẠT LẠI kinh nghiệm ĐÃ CÓ; TUYỆT ĐỐI không thêm skill mới.
Có LLM -> prompt nghiêm ngặt. Offline -> heuristic chỉ chuẩn hóa dòng đã nhắc tới skill.
"""
import re
from . import config, llm
from .taxonomy import Taxonomy

SUGGEST_PROMPT = """Bạn là chuyên gia viết CV cho vị trí {role}.
Viết lại một số dòng trong CV dưới đây cho khớp ngôn ngữ nhà tuyển dụng, mạnh và đo lường hơn.

RÀNG BUỘC TUYỆT ĐỐI:
- CHỈ diễn đạt lại kinh nghiệm ĐÃ CÓ. CẤM thêm skill/công cụ/con số mà CV không nhắc tới.
- Dòng nào đã tốt/không cải thiện được -> BỎ QUA.
- Giữ đúng sự thật; chỉ đổi cách trình bày (động từ mạnh, "hành động + công cụ + kết quả").

CV:
\"\"\"
{cv}
\"\"\"

CHỈ trả JSON hợp lệ, KHÔNG markdown, KHÔNG giải thích:
{{"suggestions":[{{"original":"<nguyên văn>","suggested":"<viết lại>","reason":"<vì sao khớp JD hơn>"}}]}}"""

_ACTION = "Phân tích và trình bày"


class CvSuggester:
    def __init__(self, taxonomy: Taxonomy, offline: bool = None):
        self.tax = taxonomy
        self.offline = config.OFFLINE_LLM if offline is None else offline
        self.aliases = [
            (s["canonical_name"], a.lower())
            for s in taxonomy.skills
            for a in [s["canonical_name"], *s.get("aliases", [])]
        ]

    def _line_skills(self, low: str) -> list:
        found = []
        for canon, alias in self.aliases:
            if not alias:
                continue
            if re.fullmatch(r"[a-z0-9]+", alias):
                hit = re.search(r"\b" + re.escape(alias) + r"\b", low) is not None
            else:
                hit = alias in low
            if hit and canon not in found:
                found.append(canon)
        return found

    def _offline(self, cv_text: str) -> list:
        out = []
        for raw in cv_text.splitlines():
            line = raw.strip(" -•\t")
            if len(line) < 12 or line[0].islower():
                continue
            skills = self._line_skills(line.lower())
            if not skills:
                continue
            tools = ", ".join(skills[:3])
            out.append({
                "original": line,
                "suggested": f"{_ACTION} dữ liệu bằng {tools}: {line[0].lower() + line[1:]}",
                "reason": f"Đưa công cụ ({tools}) lên đầu theo cách JD hay mô tả, giữ nguyên nội dung.",
            })
            if len(out) >= 4:
                break
        return out

    def suggest(self, cv_text: str, role_name: str = "Data Analyst", level: str = "junior") -> list:
        if self.offline:
            return self._offline(cv_text)
        try:
            data = llm.complete_json(SUGGEST_PROMPT.format(role=role_name, cv=cv_text), 1800)
            items = []
            for s in data.get("suggestions", []):
                o, sg = s.get("original"), s.get("suggested")
                if o and sg and o.strip() != sg.strip():
                    items.append({"original": o, "suggested": sg, "reason": s.get("reason", "")})
            return items
        except Exception:  # noqa: BLE001 - lỗi LLM -> heuristic an toàn
            return self._offline(cv_text)

    @staticmethod
    def export_markdown(accepted: list) -> str:
        lines = ["# CV (bản gợi ý chỉnh sửa)", "",
                 "> Các dòng dưới đây được viết lại cho khớp ngôn ngữ JD. Kiểm tra lại trước khi dùng.", ""]
        for s in accepted:
            sug = (s.get("suggested") or "").strip()
            if sug:
                lines.append(f"- {sug}")
        if len(lines) == 4:
            lines.append("- (chưa có mục nào được chấp nhận)")
        return "\n".join(lines) + "\n"
