# SkillBridge

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Java](https://img.shields.io/badge/Java-17-007396?logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4-6DB33F?logo=springboot&logoColor=white)
![Thymeleaf](https://img.shields.io/badge/Thymeleaf-005F0F?logo=thymeleaf&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Phân tích khoảng cách kỹ năng: đối chiếu **CV** với **nhiều JD thật** của vị trí mơ ước, chỉ ra
đang thiếu kỹ năng gì (có bằng chứng), rồi sinh **lộ trình học cá nhân hóa** + mini-project.

Hệ thống 2 phần, giao tiếp qua HTTP:

| Phần | Ngôn ngữ | Vai trò | Thư mục |
|---|---|---|---|
| **Core / AI** | Python + FastAPI | Pipeline AI: trích skill → chuẩn hóa → cầu thị trường → gap → lộ trình | [`core/`](core/) |
| **App / UI** | Java + Spring Boot + Thymeleaf | Web UI: upload CV, xác nhận kỹ năng, xem kết quả + lộ trình | [`app/`](app/) |

## Chạy nhanh (demo, không cần API key)

**1. Core (terminal 1):**
```bash
cd core && MOCK=1 python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
**2. App (terminal 2):**
```bash
cd app && ./mvnw spring-boot:run
```
Mở <http://localhost:8080>. Docs API: <http://localhost:8000/docs>.

> Chạy pipeline AI thật (Claude/OpenAI/Groq/Gemini/Ollama) hoặc bộ trích offline: xem
> [`core/README.md`](core/README.md).

## Công nghệ

- **Core:** Python, FastAPI, Uvicorn, sentence-transformers (embedding), Anthropic / OpenAI-compatible SDK.
- **App:** Java 17, Spring Boot 4, Thymeleaf, RestClient.
- **Tài liệu chi tiết:** [`core/README.md`](core/README.md) (cách chạy core + đa provider), [`app/README.md`](app/README.md).

## Ghi chú dữ liệu

- Data Analyst dùng **25 JD thật**; 7 role IT còn lại dùng **JD mẫu tự sinh**.
- Bộ dữ liệu thô và cache **không** được commit (xem `.gitignore`).

## License

Phát hành theo giấy phép **MIT** — xem [`LICENSE`](LICENSE).
