# CHANGELOG

Các cải tiến so với bản gốc (gói nộp).

## Sửa lỗi (bug fixes)

- **Readiness band vô nghĩa** — `analyze._band` dùng `pct // 1` (không làm gì) nên dải luôn rộng
  đúng 1% ("khoảng 50–51%"), lệch với fixture/README. Sửa thành dải 10 điểm ("khoảng 50–60%"),
  pct thật luôn nằm trong dải.
- **Nhãn sai sau khi xác nhận** — bấm "Không dùng"/"Biết sơ" khiến MỌI skill (kể cả skill có
  trong >50% JD) rơi xuống "Ít quan trọng". Sửa: skill hiếm đã bị lọc ở bước trên, nên gap đã
  xác nhận là **"Ưu tiên cao"** (và được tự tick vào lộ trình). Skill thật sự hiếm vẫn "Ít quan trọng".
- **App treo → Whitelabel** — client HTTP của app cắt request sớm (ReadTimeout) khi core xử lý
  vài giây. Dùng client JDK, timeout rộng (kết nối 10s / đọc 180s); bắt thêm lỗi mạng/timeout và
  lỗi bất kỳ → banner thân thiện, không còn trang lỗi trắng.
- **Gợi ý viết lại CV vô nghĩa (offline)** — bộ luật chỉ lặp lại skill đã có trong dòng. Bỏ hẳn;
  tính năng gate theo LLM: offline hiện thông báo "cần bật AI (LLM)", LLM mode cho gợi ý thật.

## Tăng tốc

- **Trích JD song song** (`service._market`) — 25 JD trích đồng thời thay vì tuần tự; ở chế độ LLM
  giảm cold-start ~62s → ~10s.
- **Nhớ cầu thị trường trong tiến trình** — `/analyze` lần đầu ~1.5s, các lần sau ~10ms (hết cảnh
  mỗi lần tải trang lại trích lại 25 JD).
- **`core/prewarm.py`** — nạp sẵn cache trích JD trước demo (chạy cùng provider/model với core).

## Đa nhà cung cấp LLM (bền hơn khi đổi sang OpenAI)

- Cache LLM **khóa theo `provider:model`** — đổi provider tự tính lại, không trả nhầm kết quả cũ.
- **Fail-fast** khi `LLM_PROVIDER=openai` mà `OPENAI_MODEL` lại là `claude-*` (báo lỗi rõ).
- `requirements.txt` thêm `openai`; `.env.example` cảnh báo phải đặt `OPENAI_MODEL` riêng.

## Giao diện

- **Hình nền có mode**: Trơn / 🐱 Mèo / 🐟 Cá / 🐦 Chim — rải nhân vật nhỏ nhiều màu (thuần
  CSS/SVG), lưu theo trình duyệt, mặc định Trơn. Bộ chọn ở góc phải header.
- **Quầng chữ** cho phần chữ ngoài card + giảm độ đậm nền để chữ không chìm vào hoạ tiết.

## Dữ liệu & tài liệu

- Thêm resources cho `sk_feature_eng` → 100/100 skill có tài liệu học.
- Bỏ tham chiếu chết `TECHNICAL_REPORT.md` trong `extract.py`.
- Ghi chú tính năng nền trong `app/README.md`.
