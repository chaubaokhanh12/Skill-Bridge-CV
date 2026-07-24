"""config.py — Một nguồn sự thật cho hằng số, tham số và đường dẫn.

Gom mọi "magic number" + biến môi trường về đây để dễ đọc, dễ chỉnh, dễ tái dùng.
Không import module nặng ở đây (chỉ os) — an toàn để import ở bất kỳ đâu.
"""
import os

from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Đường dẫn (BASE_DIR = thư mục core/, cha của gói skillbridge/)
# --------------------------------------------------------------------------- #
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_PKG_DIR)

# Nạp core/.env vào os.environ nếu có (không ghi đè biến đã export sẵn trong shell).
load_dotenv(os.path.join(BASE_DIR, ".env"))


def path(*parts: str) -> str:
    """Ghép đường dẫn tuyệt đối tính từ thư mục core/."""
    return os.path.join(BASE_DIR, *parts)


DATA_DIR = path("data")
FIXTURES_DIR = path("fixtures")
ROLES_PATH = path("data", "roles.json")
TAXONOMY_PATH = path("data", "taxonomy.json")
RESOURCES_PATH = path("data", "resources.json")
CACHE_DIR = os.getenv("CACHE_DIR", path(".cache"))

# --------------------------------------------------------------------------- #
# Cờ vận hành
# --------------------------------------------------------------------------- #
MOCK = os.getenv("MOCK") == "1"
OFFLINE_LLM = os.getenv("OFFLINE_LLM") == "1"
CACHE_DISABLED = os.getenv("CACHE_DISABLED") == "1"

# --------------------------------------------------------------------------- #
# LLM (đa nhà cung cấp). provider == "anthropic" -> Claude; còn lại -> OpenAI-compatible
# (OpenAI, Groq, Gemini, OpenRouter, Ollama... qua OPENAI_BASE_URL).
# --------------------------------------------------------------------------- #
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
ANTHROPIC_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"
OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "").strip() or None


def resolve_provider() -> str:
    if LLM_PROVIDER:
        return LLM_PROVIDER
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "anthropic"


# --------------------------------------------------------------------------- #
# Tầng chuẩn hóa (taxonomy)
# --------------------------------------------------------------------------- #
EMB_MODEL = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")
EMB_THRESHOLD = float(os.getenv("EMB_THRESHOLD", "0.62"))  # cosine tối thiểu để khớp embedding

# --------------------------------------------------------------------------- #
# Tầng phân tích (cầu thị trường + gap + readiness)
# --------------------------------------------------------------------------- #
IMPORTANCE_WEIGHT = {"required": 1.0, "preferred": 0.6, "nice_to_have": 0.3}
COVERAGE_VALUE = {"covered": 1.0, "partial": 0.5, "missing": 0.0}
OVERRIDE_STATUS = {"have": "covered", "partial": "partial", "none": "missing"}

LABEL_HIGH = "Ưu tiên cao"
LABEL_CONFIRM = "Cần xác nhận"
LABEL_MET = "Đã đáp ứng"
LABEL_LOW = "Ít quan trọng"

CORE_FREQ = 0.6  # freq ≥ ngưỡng này => coi là "skill core"
PARTIAL_CONF_MAX = float(os.getenv("PARTIAL_CONF_MAX", "0.72"))  # conf < ngưỡng => partial

# --------------------------------------------------------------------------- #
# Tầng lộ trình (roadmap)
# --------------------------------------------------------------------------- #
LEVELS = ("junior", "mid", "senior")
LEVEL_WEEKS = {"beginner": 1, "intermediate": 2, "advanced": 2}   # số tuần theo độ khó skill
LEVEL_PHASE = {"beginner": "Nền tảng", "intermediate": "Kỹ năng chính", "advanced": "Nâng cao"}
LEVEL_HOURS = {"beginner": 6, "intermediate": 9, "advanced": 12}  # giờ mặc định khi skill chưa có resource
LEVEL_DIFF = {"beginner": "Cơ bản", "intermediate": "Trung cấp", "advanced": "Nâng cao"}
LEVEL_BRIEF = {
    "junior": "người học TRÌNH ĐỘ JUNIOR — mini-project ở mức nền tảng, phạm vi nhỏ, rõ ràng.",
    "mid": "người học TRÌNH ĐỘ MID — mini-project vừa sức, có xử lý dữ liệu thực tế đa dạng.",
    "senior": "người học TRÌNH ĐỘ SENIOR — mini-project nâng cao, có tối ưu/quy mô/độ phức tạp cao.",
}


def norm_level(level: str) -> str:
    return level if level in LEVELS else "junior"
