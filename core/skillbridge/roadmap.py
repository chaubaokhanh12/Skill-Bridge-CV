"""roadmap.py — Tầng 6: lộ trình học chi tiết + mini-project + capstone.

RoadmapBuilder:
  - Xếp skill theo 'requires' bằng topological sort (prereq học trước).
  - Skill khó/nhiều giờ trải nhiều tuần theo độ khó; mỗi tuần có: phase, lý do (nối cầu JD),
    mục tiêu, tài liệu (RAG — chỉ từ resources.json, không bịa URL), luyện tập, checkpoint.
  - mini_project giàu (title/goal/done_criteria/cv_bullet + deliverables/dataset/stretch/difficulty).
  - Thêm capstone + meta + mẹo portfolio.
mini_project do LLM sinh nếu có; offline/lỗi -> template chi tiết, tất định.
"""
import json
from . import config, llm
from .taxonomy import Taxonomy

# category -> (mẫu tên project, mẫu mục tiêu). {s} = tên skill.
CATEGORY_PROJECT = {
    "Query Language": ("Phân tích doanh thu bằng {s}", "viết truy vấn tổng hợp trả lời câu hỏi kinh doanh"),
    "Programming": ("Tự động hóa xử lý dữ liệu bằng {s}", "dùng {s} làm sạch và tổng hợp dữ liệu tự động"),
    "Data Library": ("Khám phá dữ liệu bằng {s}", "dùng {s} phân tích và biến đổi bảng dữ liệu thật"),
    "Spreadsheet": ("Bảng điều khiển bán hàng bằng {s}", "dựng báo cáo động và công thức bằng {s}"),
    "BI Tool": ("Dashboard KPI tương tác bằng {s}", "trực quan hóa chỉ số kinh doanh bằng {s}"),
    "Analytics": ("Phân tích thống kê một tập dữ liệu thật bằng {s}", "rút ra kết luận có ý nghĩa bằng {s}"),
    "Data Preparation": ("Làm sạch bộ dữ liệu lộn xộn bằng {s}", "biến dữ liệu thô thành bộ sẵn sàng phân tích"),
    "Data Engineering": ("Xây pipeline dữ liệu nhỏ với {s}", "đưa dữ liệu từ nguồn vào kho phân tích bằng {s}"),
    "Cloud Data": ("Truy vấn dữ liệu quy mô lớn trên {s}", "phân tích tập dữ liệu lớn bằng {s}"),
    "Visualization": ("Kể chuyện dữ liệu bằng {s}", "truyền đạt insight bằng biểu đồ {s}"),
    "Communication": ("Bài trình bày insight dữ liệu", "trình bày kết quả phân tích một cách thuyết phục"),
    "Advanced Analytics": ("Mô hình dự đoán đơn giản bằng {s}", "xây và đánh giá mô hình {s}"),
    "Frontend": ("Xây giao diện web thực tế bằng {s}", "dựng UI tương tác, responsive bằng {s}"),
    "Backend": ("Xây API dịch vụ bằng {s}", "thiết kế và hiện thực API bằng {s}"),
    "Database": ("Thiết kế và tối ưu dữ liệu với {s}", "mô hình hóa và truy vấn hiệu quả bằng {s}"),
    "DevOps": ("Tự động hóa triển khai với {s}", "dựng quy trình build/deploy bằng {s}"),
    "QA": ("Bộ kiểm thử cho một ứng dụng thật bằng {s}", "thiết kế và chạy kiểm thử bằng {s}"),
    "Software Engineering": ("Bài toán thực hành {s}", "vận dụng {s} vào giải quyết vấn đề kỹ thuật"),
}
DEFAULT_PROJECT = ("Dự án thực hành {s}", "ứng dụng {s} vào một bài toán thực tế")

PORTFOLIO_TIPS = [
    "Mỗi mini-project đẩy lên GitHub/portfolio ngay khi xong — nhà tuyển dụng xem được là điểm cộng lớn.",
    "Viết mỗi dự án theo cấu trúc: bài toán → cách làm → kết quả → điều học được.",
    "Biến done_criteria và cv_bullet thành gạch đầu dòng trong CV; ưu tiên các skill 'Ưu tiên cao'.",
]

ROADMAP_SKILL_PROMPT = """Bạn là mentor xây lộ trình học.
Đối tượng: {level_brief}
Với skill dưới đây, sinh MỘT mini-project thực tế, cụ thể, đo lường được, đúng phong cách
portfolio VÀ đúng tầm trình độ trên.

RÀNG BUỘC:
- CHỈ dùng resource được cung cấp; TUYỆT ĐỐI không bịa link mới.
- done_criteria đo được; deliverables là sản phẩm nộp được; cv_bullet viết dạng thành tích.

SKILL (JSON):
{skill}

CHỈ trả JSON hợp lệ, KHÔNG markdown, KHÔNG giải thích:
{{"skill_id":"...","title":"...","goal":"...","difficulty":"...",
"dataset":"...","done_criteria":["...","..."],"deliverables":["...","..."],
"stretch":"...","cv_bullet":"..."}}"""


class RoadmapBuilder:
    def __init__(self, taxonomy: Taxonomy, resources_path: str = None, offline: bool = None):
        self.tax = taxonomy
        with open(resources_path or config.RESOURCES_PATH, encoding="utf-8") as f:
            self.resources = json.load(f)
        self.offline = config.OFFLINE_LLM if offline is None else offline

    # -- topological sort --------------------------------------------------
    def topological_sort(self, skill_ids: list) -> list:
        ordered = list(dict.fromkeys(skill_ids))
        inset = set(ordered)
        deps = {sid: [r for r in self.tax.requires(sid) if r in inset] for sid in ordered}
        order, done = [], set()
        while len(order) < len(ordered):
            progressed = False
            for sid in ordered:
                if sid in done:
                    continue
                if all(r in done for r in deps[sid]):
                    order.append(sid); done.add(sid); progressed = True; break
            if not progressed:  # chu trình -> nối phần còn lại
                for sid in ordered:
                    if sid not in done:
                        order.append(sid); done.add(sid)
                break
        return order

    # -- nội dung học (tất định) -------------------------------------------
    def _why(self, sid, level, order_set, demand, total_jd) -> str:
        d = (demand or {}).get(sid)
        if d and d.get("jd_count"):
            req = d.get("required_count", 0)
            tail = f", bắt buộc ở {req} nơi" if req else ""
            njd = d.get("total_jd") or total_jd or "?"
            return (f"Xuất hiện trong {d['jd_count']}/{njd} JD của vị trí này{tail} "
                    f"— đây là khoảng trống đáng ưu tiên lấp.")
        prereqs = [r for r in self.tax.requires(sid) if r in order_set]
        if prereqs:
            names = ", ".join(self.tax.canonical_name(r) for r in prereqs)
            return f"Kỹ năng {config.LEVEL_DIFF.get(level, '').lower()} xây trên nền {names}; học sau khi vững phần đó."
        return f"Kỹ năng {config.LEVEL_PHASE.get(level, 'cốt lõi').lower()} cho vị trí này, nên nắm sớm."

    def _objectives(self, sid, level) -> list:
        s = self.tax.canonical_name(sid)
        base = [f"Nắm vững khái niệm cốt lõi và cú pháp/nguyên tắc của {s}.",
                f"Tự tay áp dụng {s} vào một bài toán thật từ đầu đến cuối."]
        base.append(f"Xử lý được tình huống phức tạp/tối ưu khi dùng {s}." if level == "advanced"
                    else f"Giải thích được kết quả {s} cho người không chuyên.")
        return base

    def _practice(self, sid) -> list:
        s = self.tax.canonical_name(sid)
        return [f"Gõ tay lại 2–3 ví dụ trong tài liệu (không copy) để nhớ {s}.",
                f"Tự đặt một bài toán nhỏ và dùng {s} giải trọn vẹn.",
                f"Ghi chú 5 lỗi/điểm dễ nhầm khi dùng {s} để tra lại sau."]

    def _checkpoint(self, sid) -> str:
        return f"Tự kiểm: giải một bài mới với {self.tax.canonical_name(sid)} trong ~30 phút mà không tra cứu liên tục."

    @staticmethod
    def _dataset_hint(category) -> str:
        if category in ("BI Tool", "Visualization", "Spreadsheet"):
            return "Dùng dữ liệu bán hàng/marketing mẫu (Kaggle Superstore) hoặc số liệu thật đã ẩn danh."
        if category in ("Analytics", "Advanced Analytics"):
            return "Chọn bộ dữ liệu có biến số rõ ràng (Kaggle, UCI ML Repository)."
        if category in ("Data Engineering", "Cloud Data", "Database"):
            return "Dùng nguồn dữ liệu công khai đủ lớn (BigQuery public datasets, data.gov)."
        if category in ("Frontend", "Backend"):
            return "Dựng trên một ý tưởng ứng dụng nhỏ có thật (todo, blog, dashboard cá nhân)."
        return "Chọn một bộ dữ liệu/ý tưởng công khai hoặc từ công việc đã ẩn danh."

    def _template_project(self, sid, level) -> dict:
        s = self.tax.canonical_name(sid)
        cat = self.tax.category(sid)
        title_t, goal_t = CATEGORY_PROJECT.get(cat, DEFAULT_PROJECT)
        return {
            "title": title_t.format(s=s),
            "goal": f"Chứng minh khả năng {goal_t.format(s=s)}.",
            "difficulty": config.LEVEL_DIFF.get(level, "Trung cấp"),
            "dataset": self._dataset_hint(cat),
            "done_criteria": [
                f"Hoàn thành một sản phẩm dùng {s} có thể tái chạy.",
                "Ghi lại quy trình và kết quả bằng tài liệu hoặc dashboard rõ ràng.",
                "Rút ra ít nhất 3 điểm/insight có thể hành động và trình bày ngắn gọn.",
            ],
            "deliverables": [
                "File quy trình (notebook/script/repo) có chú thích từng bước.",
                "Một báo cáo hoặc bản demo trình bày kết quả.",
                "README mô tả bài toán và cách chạy lại.",
            ],
            "stretch": f"Mở rộng: tự động hóa lại quy trình hoặc thêm một chiều mới bằng {s}.",
            "cv_bullet": f"Ứng dụng {s} để giải một bài toán thực tế và tạo sản phẩm đưa vào portfolio.",
        }

    # -- mini-project qua LLM (làm giàu phần sáng tạo, 1 call/skill để streaming được) --
    def _llm_project_for_skill(self, sid: str, level: str) -> dict:
        ctx = {
            "skill_id": sid, "name": self.tax.canonical_name(sid),
            "resources": [{"title": r["title"], "url": r["url"]} for r in self.resources.get(sid, [])],
        }
        try:
            brief = config.LEVEL_BRIEF.get(level, config.LEVEL_BRIEF["junior"])
            return llm.complete_json(ROADMAP_SKILL_PROMPT.format(
                level_brief=brief, skill=json.dumps(ctx, ensure_ascii=False)), 900)
        except Exception:  # noqa: BLE001 - lỗi/rỗng -> template fallback ở _merge_project
            return {}

    def _merge_project(self, sid, level, llm_proj) -> dict:
        proj = self._template_project(sid, level)
        if llm_proj:
            for k in ("title", "goal", "difficulty", "dataset", "cv_bullet", "stretch"):
                if llm_proj.get(k):
                    proj[k] = llm_proj[k]
            for k in ("done_criteria", "deliverables"):
                v = llm_proj.get(k)
                if isinstance(v, list) and v:
                    proj[k] = list(v)
        return proj

    def _plan_weeks(self, sid):
        """(số tuần, tài liệu chia đều vào từng tuần). Nhịp = hours_per_week nên tuần ≈ đều."""
        res = [{"title": r["title"], "url": r["url"], "hours": int(r.get("hours", 0) or 0)}
               for r in self.resources.get(sid, [])]
        n = max(1, min(config.LEVEL_WEEKS.get(self.tax.level(sid), 2), 3))
        weeks = [[] for _ in range(n)]
        for r in sorted(res, key=lambda x: -x["hours"]):  # tài liệu nặng vào tuần ít giờ nhất
            i = min(range(n), key=lambda k: sum(x["hours"] for x in weeks[k]))
            weeks[i].append(r)
        return n, weeks

    def _capstone(self, order) -> dict:
        names = [self.tax.canonical_name(s) for s in order]
        lead = names[0] if names else "kỹ năng nền"
        return {
            "title": "Dự án tổng hợp: mini-portfolio",
            "goal": (f"Kết hợp các kỹ năng vừa học ({', '.join(names)}) vào MỘT sản phẩm hoàn chỉnh "
                     f"trên một chủ đề bạn quan tâm."),
            "skills_used": names,
            "done_criteria": [
                f"Xây một sản phẩm đầu-cuối dùng {lead} và các kỹ năng liên quan.",
                "Có phần trình bày kết quả/insight rõ ràng cho người ngoài.",
                "Đăng công khai (GitHub/portfolio) kèm README mô tả.",
            ],
            "cv_bullet": "Thực hiện dự án đầu-cuối tổng hợp nhiều kỹ năng, công bố công khai kèm tài liệu.",
        }

    # -- API chính (streaming) ----------------------------------------------
    def build_stream(self, skill_ids, hours_per_week=5, demand=None, role_name=None,
                     total_jd=None, level="junior"):
        """Sinh lộ trình dạng generator: yield {"type": ..., "data": ...} theo thứ tự
        meta -> week (nhiều lần) -> capstone -> tips -> done.
        meta/capstone/tips tất định (không cần LLM) nên gửi được ngay. mini_project của
        tuần cuối mỗi skill gọi 1 LLM call riêng (thay vì 1 batch call cho tất cả skill)
        để mỗi tuần trả về ngay khi xong, không phải đợi hết N skill."""
        hpw = max(1, int(hours_per_week))
        order = self.topological_sort(skill_ids)
        order_set = set(order)

        plan = [(sid, *self._plan_weeks(sid)) for sid in order]  # tất định, tính 1 lần
        total_weeks = sum(n for _, n, _ in plan)
        total_hours = total_weeks * hpw
        yield {"type": "meta", "data": {
            "total_weeks": total_weeks, "hours_per_week": hpw, "total_hours": total_hours,
            "skill_count": len(order),
            "summary": (f"Lộ trình {total_weeks} tuần (~{total_hours} giờ, {hpw} giờ/tuần) "
                        f"qua {len(order)} kỹ năng còn thiếu"
                        + (f" cho vị trí {role_name}" if role_name else "")
                        + ", kết thúc bằng một dự án tổng hợp để đưa vào CV/portfolio."),
        }}

        wk = 0
        for sid, n_weeks, res_by_week in plan:
            lvl = self.tax.level(sid)
            phase = config.LEVEL_PHASE.get(lvl, "Kỹ năng chính")
            objectives, practice = self._objectives(sid, level), self._practice(sid)

            for i in range(n_weeks):
                wk += 1
                is_last = (i == n_weeks - 1)
                if n_weeks > 1:
                    focus = ("Nắm nền tảng và cú pháp cốt lõi." if i == 0
                             else "Thực hành sâu trên bài toán thật và hoàn thành mini-project." if is_last
                             else "Luyện tập nâng cao và củng cố.")
                    skill_label = f"{self.tax.canonical_name(sid)} · phần {i + 1}/{n_weeks}"
                else:
                    focus = "Học lý thuyết cốt lõi rồi thực hành ngay bằng mini-project."
                    skill_label = self.tax.canonical_name(sid)
                mini_project = None
                if is_last:
                    llm_proj = {} if self.offline else self._llm_project_for_skill(sid, level)
                    mini_project = self._merge_project(sid, level, llm_proj)
                yield {"type": "week", "data": {
                    "week": wk, "skill": skill_label, "skill_id": sid, "phase": phase,
                    "level": config.LEVEL_DIFF.get(lvl, "Trung cấp"), "focus": focus,
                    "why": self._why(sid, level, order_set, demand, total_jd),
                    "objectives": objectives if i == 0 else [],
                    "estimated_hours": hpw,
                    "resources": res_by_week[i] if i < len(res_by_week) else [],
                    "practice": practice[:2] if i == 0 else practice[1:],
                    "checkpoint": self._checkpoint(sid),
                    "mini_project": mini_project,
                }}

        yield {"type": "capstone", "data": self._capstone(order)}
        yield {"type": "tips", "data": list(PORTFOLIO_TIPS)}
        yield {"type": "done", "data": None}

    # -- API chính (không streaming, gom từ build_stream) --------------------
    def build(self, skill_ids, hours_per_week=5, demand=None, role_name=None, total_jd=None, level="junior") -> dict:
        meta, weeks, capstone, tips = None, [], None, []
        for item in self.build_stream(skill_ids, hours_per_week, demand, role_name, total_jd, level):
            if item["type"] == "meta":
                meta = item["data"]
            elif item["type"] == "week":
                weeks.append(item["data"])
            elif item["type"] == "capstone":
                capstone = item["data"]
            elif item["type"] == "tips":
                tips = item["data"]
        return {"meta": meta, "weeks": weeks, "capstone": capstone, "portfolio_tips": tips}
