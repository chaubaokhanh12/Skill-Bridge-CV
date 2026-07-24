"""llm.py — Trừu tượng hóa LLM đa nhà cung cấp.

LLMClient là interface; hai hiện thực:
  - AnthropicClient          (Claude)
  - OpenAICompatibleClient   (OpenAI, Groq, Gemini, OpenRouter, Ollama... qua base_url)

get_client() chọn provider theo cấu hình (config.resolve_provider) và cache singleton.
complete_json() có cache theo (provider, model, prompt) => cùng input cho cùng kết quả
(tất định, không gọi lặp); đổi provider/model thì tự tính lại, không trả nhầm cache cũ.

SDK (anthropic / openai) chỉ import khi THẬT SỰ gọi — nên MOCK/offline không cần cài.
"""
import re
import json
from abc import ABC, abstractmethod

from . import config
from .cache import cached


def parse_json(text: str) -> dict:
    """Bóc JSON khỏi output LLM (gỡ code-fence, lấy khối {...} đầu tiên nếu cần)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t[:4].lower() == "json":
            t = t[4:].strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


class LLMClient(ABC):
    """Giao diện tối giản: đưa prompt, nhận text (temperature=0 để tất định)."""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 1500) -> str:
        ...


class AnthropicClient(LLMClient):
    def __init__(self, model: str = None):
        import anthropic  # lazy
        self._client = anthropic.Anthropic()
        self._model = model or config.ANTHROPIC_MODEL

    def complete(self, prompt: str, max_tokens: int = 1500) -> str:
        r = self._client.messages.create(
            model=self._model, max_tokens=max_tokens, temperature=0,
            messages=[{"role": "user", "content": prompt}])
        return r.content[0].text


class OpenAICompatibleClient(LLMClient):
    """OpenAI SDK trỏ tới bất kỳ endpoint tương thích OpenAI (Groq/Gemini/Ollama/...)."""

    def __init__(self, model: str = None, base_url: str = None, api_key: str = None):
        import os
        self._model = model or config.OPENAI_MODEL
        if self._model.lower().startswith("claude"):  # fail-fast: bẫy cấu hình hay gặp
            raise ValueError(
                f"OPENAI_MODEL='{self._model}' trông như model Claude — không hợp lệ khi "
                "LLM_PROVIDER=openai. Hãy đặt OPENAI_MODEL (vd 'gpt-4o-mini'); thường do .env "
                "vẫn còn LLM_MODEL=claude-... mà chưa set OPENAI_MODEL riêng.")
        from openai import OpenAI  # lazy
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if key and not key.isascii():
            raise ValueError("OPENAI_API_KEY chứa ký tự lạ (non-ASCII) — copy lại key sạch.")
        self._client = OpenAI(api_key=key or None, base_url=base_url or config.OPENAI_BASE_URL)

    def complete(self, prompt: str, max_tokens: int = 1500) -> str:
        r = self._client.chat.completions.create(
            model=self._model, max_tokens=max_tokens, temperature=0,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content


_client: LLMClient = None


def get_client() -> LLMClient:
    """Trả LLMClient theo provider cấu hình (singleton, khởi tạo lười)."""
    global _client
    if _client is None:
        provider = config.resolve_provider()
        _client = AnthropicClient() if provider == "anthropic" else OpenAICompatibleClient()
    return _client


def reset_client() -> None:
    """Xóa singleton (hữu ích cho test khi đổi provider)."""
    global _client
    _client = None


def _cache_tag() -> str:
    """Nhãn 'provider:model' để KHÓA cache tách theo nhà cung cấp — đổi provider/model thì
    tính lại thay vì trả nhầm kết quả provider cũ. Đọc từ config (KHÔNG dựng client) nên
    cache-hit vẫn không cần SDK/API key."""
    provider = config.resolve_provider()
    model = config.ANTHROPIC_MODEL if provider == "anthropic" else config.OPENAI_MODEL
    return f"{provider}:{model}"


@cached
def _complete_json(cache_tag: str, prompt: str, max_tokens: int) -> dict:
    # cache_tag chỉ tham gia KHÓA cache (xem _cache_tag), không dùng trong thân hàm.
    return parse_json(get_client().complete(prompt, max_tokens))


def complete_json(prompt: str, max_tokens: int = 1500) -> dict:
    """Gọi LLM và parse JSON, cache tất định theo (provider, model, prompt, max_tokens)."""
    return _complete_json(_cache_tag(), prompt, max_tokens)
