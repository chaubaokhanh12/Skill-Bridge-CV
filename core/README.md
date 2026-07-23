# SkillBridge — CORE / AI Service

Service HTTP (FastAPI) phân tích khoảng cách kỹ năng CV ↔ thị trường JD, và sinh lộ trình học.
Đồng đội Java chỉ cần **API contract** + link `/docs`.

Logic nằm trong gói `skillbridge/`; `main.py` là tầng API mỏng.

---

## 1. Cài đặt

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Chỉ chạy **MOCK** thì không bắt buộc cài xong torch/anthropic (nạp lười).

## 2. Chạy MOCK (không cần API key)

```bash
MOCK=1 uvicorn main:app --host 0.0.0.0 --port 8000
```
Mở <http://localhost:8000/docs>. Mọi request `/analyze`, `/roadmap`, `/scan-cv`,
`/cv-suggestions` trả `fixtures/*.json`.

## 3. Chạy THẬT

Cần khóa của **một** nhà cung cấp LLM. Mặc định Anthropic (Claude); hoặc bất kỳ endpoint
tương thích OpenAI.

**Claude (Anthropic):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
MOCK=0 uvicorn main:app --host 0.0.0.0 --port 8000
```

**OpenAI / Groq / Gemini / OpenRouter / Ollama** (endpoint tương thích OpenAI):
```bash
pip install openai
export LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"   # Groq; đổi theo provider
export OPENAI_MODEL="llama-3.3-70b-versatile"
MOCK=0 uvicorn main:app --host 0.0.0.0 --port 8000
```
- Gemini: `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, `OPENAI_MODEL=gemini-2.0-flash`
- Ollama (local, free): `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`

**Chạy thật KHÔNG cần API key** (bộ trích luật + embedding thật/alias): `MOCK=0 OFFLINE_LLM=1 uvicorn ...`

Kiểm chế độ: <http://localhost:8000/health> → `{"mock": false}`.

## 4. Endpoint

| Method | Path | Ghi chú |
|--------|------|---------|
| GET  | `/roles`          | dropdown vị trí (8 role) |
| POST | `/analyze`        | multipart: `cv_file`, `role_id`, `overrides`, `level`, `confirmed_skills` |
| POST | `/scan-cv`        | multipart: `cv_file` → skill để xác nhận |
| POST | `/cv-suggestions` | multipart: `cv_file`, `role_id`, `level` |
| POST | `/cv-export`      | json: `{accepted[], format}` → tải .md |
| POST | `/roadmap`        | json: `{role_id, level, hours_per_week, skill_ids[]}` |

Mọi lỗi: HTTP **422**, shape `{ "code", "message" }`. `band` luôn là chuỗi dải.

## 5. Docker
```bash
docker build -t skillbridge-core .
docker run --rm -p 8000:8000 skillbridge-core                          # MOCK
docker run --rm -p 8000:8000 -e MOCK=0 -e ANTHROPIC_API_KEY=sk-... skillbridge-core
```

## 6. Kiểm thử nhanh
```bash
MOCK=1 uvicorn main:app --port 8000       # rồi mở terminal khác:
curl http://localhost:8000/health          # {"status":"ok","mock":true}
curl http://localhost:8000/roles           # 8 role
```

## 7. Dữ liệu
- `data/roles.json` — 8 vị trí IT.
- `data/jds/<role>/` — **Data Analyst: 25 JD thật**; 7 role còn lại **JD mẫu tự sinh**. Thay bằng
  JD thật của bạn: bỏ file `.txt` vào thư mục `data/jds/<role_id>/` tương ứng.
- `data/taxonomy.json` — 100 skill (alias + requires DAG). `data/resources.json` — link học thật.

## 8. Biến môi trường chính

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `MOCK` | `0` | `1` → trả fixtures |
| `OFFLINE_LLM` | — | `1` → bộ trích luật, không gọi API |
| `LLM_PROVIDER` | auto | `anthropic` \| `openai` (và tương thích) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | — | khóa provider |
| `OPENAI_BASE_URL` / `OPENAI_MODEL` | — | endpoint + model tương thích OpenAI |
| `EMB_THRESHOLD` | `0.62` | ngưỡng cosine lớp embedding |
| `CACHE_DIR` / `CACHE_DISABLED` | `./.cache` | cache LLM |
