# SkillBridge — App (Java + Spring Boot)

Web UI cho người dùng upload CV, gọi service AI (Python core ở `http://localhost:8000`),
hiển thị **khoảng cách kỹ năng** + **lộ trình học**, giữ đúng API contract của core.

- Spring Boot 4 + Thymeleaf (server-side render) + `RestClient` gọi core.
- State `overrides` + CV giữ trong `HttpSession` (bấm xác nhận không phải upload lại).
- Không cần cài Maven — dùng sẵn Maven Wrapper (`mvnw`).

---

## Chạy (2 bước)

**1) Bật service AI (Python core)** — ở thư mục `../core`:

```bash
cd ../core && MOCK=1 python -m uvicorn main:app --port 8000
```

**2) Bật app Java** — ở thư mục này:

```bash
./mvnw spring-boot:run
```

Mở **http://localhost:8080** → chọn vị trí + cấp độ, tải CV của bạn (.pdf/.docx/.txt),
rồi đi theo các bước trên màn hình.

> Windows CMD/PowerShell dùng `mvnw.cmd spring-boot:run`.

---

## Luồng dùng thử

1. Trang chủ: chọn role (từ `GET /roles`), kéo slider giờ/tuần, tải CV → **Phân tích ngay**.
2. Xem thẻ **mức độ sẵn sàng** (dùng nguyên chuỗi `band`, vd "khoảng 50–60%") + danh sách
   thẻ skill có badge màu theo nhãn + dòng bằng chứng + thanh độ phổ biến.
3. Skill **"Cần xác nhận"** có 3 nút **Có / Biết sơ / Không** → cập nhật `overrides` →
   phân tích lại (không upload lại CV).
4. Chọn skill muốn học → **Tạo lộ trình học** → xem lộ trình theo tuần + mini-project.

> "Wow moment" (human-in-the-loop): bấm **Không** ở một skill "Cần xác nhận" → readiness đổi.
> Hiệu ứng này chỉ thấy khi core chạy **MOCK=0** (pipeline thật). Ở MOCK=1 core trả fixture
> cố định nên số không đổi — nhưng cơ chế gửi override vẫn chạy đúng.

---

## Giao diện

Góc phải header có 2 công tắc, lưu theo trình duyệt (localStorage):

- **Sáng / tối** — nút "Chế độ tối".
- **Hình nền** — bộ chọn **○ Trơn · 🐱 Mèo · 🐟 Cá · 🐦 Chim**: rải các nhân vật nhỏ
  nhiều màu làm nền trang trí (mặc định: trơn). Thuần CSS/SVG, không ảnh hưởng dữ liệu.

## Cấu hình

`src/main/resources/application.properties`:

```
core.base-url=http://localhost:8000   # đổi nếu core chạy host/cổng khác
server.port=8080
```

## Build jar chạy độc lập

```bash
./mvnw -DskipTests package
java -jar target/app-0.0.1-SNAPSHOT.jar
```

---

## Đối chiếu Definition of Done (Mục 8)

- [x] Trang chủ: dropdown role + slider giờ/tuần + upload CV.
- [x] `POST /analyze` với file; thẻ readiness dùng `band` nguyên văn.
- [x] Danh sách thẻ skill đúng thứ tự API; badge màu theo `label`.
- [x] Mỗi thẻ có dòng bằng chứng (x/N JD · required; trạng thái CV + evidence).
- [x] Skill `needs_confirmation` có 3 nút; bấm → cập nhật `overrides` → phân tích lại.
- [x] Chân trang có dòng tự nêu giới hạn.
- [x] Chọn skill → `POST /roadmap` → lộ trình theo tuần + mini-project (title, goal,
      done_criteria, cv_bullet, resources có link thật).
- [x] Không in số thập phân giả (dùng thanh bar theo `freq`, hiển thị phần trăm nguyên).
- [x] Chạy với `MOCK=1` (fixtures) và core thật (JSON giống nhau).
- [x] Lỗi 422 từ core → banner thân thiện, không crash.
