"""cache.py — Cache tất định ra đĩa (Mục 7 spec).

Cùng input => cùng kết quả, không gọi LLM lặp, demo ổn định. Khóa = hash(tên hàm + args).
Dùng qua decorator @cached (bọc một DiskCache mặc định) hoặc trực tiếp DiskCache.
"""
import os
import json
import hashlib
import functools
from typing import Any, Callable

from . import config


class DiskCache:
    """Kho cache JSON trên đĩa, khóa theo SHA-256 của (namespace + args)."""

    def __init__(self, directory: str = None, disabled: bool = None):
        self.directory = directory or config.CACHE_DIR
        self.disabled = config.CACHE_DISABLED if disabled is None else disabled

    def _key(self, namespace: str, args: tuple, kwargs: dict) -> str:
        payload = json.dumps(
            {"fn": namespace, "args": args, "kwargs": kwargs},
            sort_keys=True, ensure_ascii=False, default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _path(self, namespace: str, key: str) -> str:
        return os.path.join(self.directory, f"{namespace}_{key}.json")

    def get_or_compute(self, namespace: str, compute: Callable[[], Any],
                       args: tuple = (), kwargs: dict = None) -> Any:
        kwargs = kwargs or {}
        if self.disabled:
            return compute()
        os.makedirs(self.directory, exist_ok=True)
        path = self._path(namespace, self._key(namespace, args, kwargs))
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass  # cache hỏng -> tính lại
        result = compute()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except (TypeError, OSError):
            pass  # không cache được cũng không sao
        return result


# Cache mặc định + decorator tiện dụng (giữ tương thích với cách gọi @cached cũ).
default_cache = DiskCache()


def cached(func: Callable) -> Callable:
    """Cache giá trị trả về của hàm (JSON-serializable) theo hash input."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return default_cache.get_or_compute(
            func.__name__, lambda: func(*args, **kwargs), args, kwargs)
    return wrapper
