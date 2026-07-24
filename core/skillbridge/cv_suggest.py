"""cv_suggest.py — Gợi ý VIẾT LẠI CV cho khớp ngôn ngữ JD (CẦN LLM).

RÀNG BUỘC CỨNG: chỉ DIỄN ĐẠT LẠI kinh nghiệm ĐÃ CÓ; TUYỆT ĐỐI không thêm skill mới.
Viết lại CV cho ra hồn (động từ mạnh + đo lường + khớp JD) cần LLM. Bộ luật offline
KHÔNG làm được việc này (chỉ lặp lại skill đã có → vô nghĩa), nên offline trả RỖNG và
để UI báo "cần bật chế độ AI (LLM)". Lỗi LLM cũng trả rỗng thay vì bịa gợi ý.
"""
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


class CvSuggester:
    def __init__(self, taxonomy: Taxonomy, offline: bool = None):
        self.tax = taxonomy
        self.offline = config.OFFLINE_LLM if offline is None else offline

    def suggest(self, cv_text: str, role_name: str = "Data Analyst", level: str = "junior") -> list:
        """Viết lại CV bằng LLM. Offline hoặc LLM lỗi -> [] (không bịa; UI báo cần LLM)."""
        if self.offline:
            return []
        try:
            data = llm.complete_json(SUGGEST_PROMPT.format(role=role_name, cv=cv_text), 1800)
            items = []
            for s in data.get("suggestions", []):
                o, sg = s.get("original"), s.get("suggested")
                if o and sg and o.strip() != sg.strip():
                    items.append({"original": o, "suggested": sg, "reason": s.get("reason", "")})
            return items
        except Exception:  # noqa: BLE001 - lỗi LLM -> thà không gợi ý còn hơn bịa
            return []

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
