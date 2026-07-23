"""errors.py — Lỗi ứng dụng dùng chung.

Mọi lỗi nghiệp vụ ném AppError; tầng API map thành { "code", "message" } + HTTP 422.
"""


class AppError(Exception):
    """Lỗi có mã + thông điệp thân thiện để trả thẳng cho client."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
