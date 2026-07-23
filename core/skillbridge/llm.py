"""llm.py — Trừu tượng hóa LLM đa nhà cung cấp.

LLMClient là interface; hai hiện thực:
  - AnthropicClient          (Claude)
  - OpenAICompatibleClient   (OpenAI, Groq, Gemini, OpenRouter, Ollama... qua base_url)

get_client() chọn provider theo cấu hình (config.resolve_provider) và cache singleton.
complete_json() bọc @cached => cùng prompt cho cùng kết quả (tất định, không gọi lặp).

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
        from openai import OpenAI  # lazy
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if key and not key.isascii():
            raise ValueError("OPENAI_API_KEY chứa ký tự lạ (non-ASCII) — copy lại key sạch.")
        self._client = OpenAI(api_key=key or None, base_url=base_url or config.OPENAI_BASE_URL)
        self._model = model or config.OPENAI_MODEL

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


@cached
def complete_json(prompt: str, max_tokens: int = 1500) -> dict:
    """Gọi LLM và parse JSON, có cache theo prompt (tất định)."""
    return parse_json(get_client().complete(prompt, max_tokens))
