# SkillBridge Core — Dockerfile (Mục 7: tránh "máy tôi chạy được")
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf

# Cài torch bản CPU trước để image nhẹ hơn (không kéo CUDA).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nạp sẵn model embedding vào image để chạy thật không cần tải lúc runtime.
# (Bỏ dòng này nếu build không có mạng — model sẽ tải ở lần /analyze đầu tiên.)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000
# Mặc định bật MOCK để container chạy được ngay không cần API key.
# Chạy thật: docker run -e MOCK=0 -e ANTHROPIC_API_KEY=sk-... ...
ENV MOCK=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
