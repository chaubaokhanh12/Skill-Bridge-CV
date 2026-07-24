"""prewarm.py — Nạp sẵn cache trích JD cho các role TRƯỚC khi demo.

Ở chế độ LLM (online), lần /analyze đầu tiên phải trích skill từ toàn bộ JD (mỗi JD 1
lời gọi LLM). Chạy script này một lần sau khi bật core để ghi sẵn cache đĩa (_cache),
nhờ đó lần /analyze đầu trong lúc demo là cache-hit -> gần như tức thì.

Chạy CÙNG môi trường (provider/model/key) với core để cache khớp khóa provider:model.

    python prewarm.py                 # nạp tất cả role
    python prewarm.py data_analyst    # chỉ 1 role

Ví dụ (LLM Claude):
    export ANTHROPIC_API_KEY=sk-ant-...
    MOCK=0 python prewarm.py data_analyst
"""
import sys
import time

from skillbridge.service import AnalysisService


def main(argv):
    svc = AnalysisService()
    roles = [argv[1]] if len(argv) > 1 else [r["id"] for r in svc.roles()]
    total = time.time()
    for rid in roles:
        try:
            role = svc.get_role(rid)
            t = time.time()
            n_jd, _ = svc._market(role)  # trích + ghi cache (song song)
            print(f"  {rid:20} {n_jd:2} JD  ->  {time.time() - t:5.1f}s")
        except Exception as e:  # noqa: BLE001 - một role lỗi không chặn role khác
            print(f"  {rid:20} LỖI: {e}")
    print(f"Pre-warm xong {len(roles)} role trong {time.time() - total:.1f}s. "
          f"Giờ /analyze sẽ dùng cache -> nhanh.")


if __name__ == "__main__":
    main(sys.argv)
