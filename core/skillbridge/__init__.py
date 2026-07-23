"""SkillBridge Core — gói lõi AI phân tích khoảng cách kỹ năng CV ↔ thị trường JD.

Kiến trúc theo tầng, mỗi tầng một trách nhiệm rõ ràng (xem ARCHITECTURE.md):

    config      — hằng số/tham số + đường dẫn + biến môi trường (một nguồn sự thật)
    errors      — AppError dùng chung ({code, message}, HTTP 422)
    cache       — DiskCache + @cached (tất định, không gọi LLM lặp)
    llm         — LLMClient (Anthropic / OpenAI-compatible) + factory theo provider
    taxonomy    — Taxonomy: chuẩn hóa skill 3 lớp (alias → embedding → unmatched)
    extract     — SkillExtractor (LLMExtractor | RuleExtractor) + đọc CV + scan CV
    analyze     — MarketAnalyzer: cầu thị trường + gap + readiness (thuần, tất định)
    roadmap     — RoadmapBuilder: lộ trình học + mini-project + capstone
    cv_suggest  — CvSuggester: gợi ý viết lại CV (không bịa skill)
    service     — AnalysisService: điều phối toàn bộ pipeline cho tầng API

Tầng API (FastAPI) nằm ở `main.py` — mỏng, chỉ map HTTP ↔ AnalysisService.
"""

__version__ = "1.0.0"
