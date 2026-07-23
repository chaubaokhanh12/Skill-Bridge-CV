"""main.py — Tầng API (FastAPI). MỎNG: chỉ map HTTP ↔ AnalysisService, không chứa logic.

3 endpoint gốc (contract Mục 1): GET /roles, POST /analyze, POST /roadmap.
Bổ sung (bản vá): POST /scan-cv, POST /cv-suggestions, POST /cv-export.
MOCK=1 -> trả fixtures/*.json (đồng đội build UI không cần API key).
Mọi lỗi -> { "code", "message" } + HTTP 422.

Chạy:  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import json
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from skillbridge import config
from skillbridge.errors import AppError
from skillbridge.service import AnalysisService

app = FastAPI(title="SkillBridge Core", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

service = AnalysisService()  # nạp roles + taxonomy (nhẹ; LLM/embedding nạp lười khi cần)


# --------------------------------------------------------------------------- #
# Xử lý lỗi: mọi lỗi -> { code, message } + HTTP 422
# --------------------------------------------------------------------------- #
@app.exception_handler(AppError)
async def _app_error(_req, exc: AppError):
    return JSONResponse(status_code=422, content={"code": exc.code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def _validation(_req, exc: RequestValidationError):
    errs = exc.errors()
    msg = "Dữ liệu vào không hợp lệ"
    if errs:
        e = errs[0]
        loc = ".".join(str(x) for x in e.get("loc", []) if x != "body")
        msg = f"{loc}: {e.get('msg', 'không hợp lệ')}".strip(": ")
    return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": msg})


# --------------------------------------------------------------------------- #
# Helpers (web-layer)
# --------------------------------------------------------------------------- #
def _fixture(name: str):
    with open(os.path.join(config.FIXTURES_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _save_temp(filename: str, content: bytes) -> str:
    suffix = os.path.splitext(filename or "")[1] or ".txt"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def _parse_overrides(raw: str) -> dict:
    try:
        ov = json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError):
        raise AppError("BAD_OVERRIDES", "overrides phải là JSON hợp lệ")
    if not isinstance(ov, dict):
        raise AppError("BAD_OVERRIDES", "overrides phải là object {skill_id: have|partial|none}")
    valid = {"have", "partial", "none"}
    clean = {}
    for k, v in ov.items():
        if v not in valid:
            raise AppError("BAD_OVERRIDES", f"Giá trị override không hợp lệ: {k}={v}")
        clean[str(k)] = v
    return clean


def _parse_confirmed(raw: str):
    if not raw or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise AppError("BAD_CONFIRMED", "confirmed_skills phải là JSON hợp lệ")
    if not isinstance(data, list):
        raise AppError("BAD_CONFIRMED", "confirmed_skills phải là mảng {skill_id, proficiency}")
    valid = {"proficient", "basic", "none"}
    out = []
    for it in data:
        if not isinstance(it, dict):
            continue
        sid, prof = it.get("skill_id"), it.get("proficiency")
        if not sid or prof not in valid:
            raise AppError("BAD_CONFIRMED", f"confirmed_skills không hợp lệ: {it}")
        out.append({"skill_id": str(sid), "proficiency": prof})
    return out


async def _read_upload(cv_file: UploadFile) -> str:
    content = await cv_file.read()
    if not content:
        raise AppError("EMPTY_CV", "File CV rỗng")
    return _save_temp(cv_file.filename, content)


def _cleanup(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/roles")
def get_roles():
    return {"roles": service.roles()}


@app.post("/analyze")
async def analyze(
    cv_file: UploadFile = File(...),
    role_id: str = Form(...),
    overrides: str = Form("{}"),
    level: str = Form("junior"),
    confirmed_skills: str = Form(None),
):
    if config.MOCK:
        return _fixture("analyze.json")
    try:
        ov = _parse_overrides(overrides)
        confirmed = _parse_confirmed(confirmed_skills)
        path = await _read_upload(cv_file)
        try:
            return service.analyze(path, role_id, ov, config.norm_level(level), confirmed)
        finally:
            _cleanup(path)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError("ANALYZE_FAILED", str(e))


@app.post("/scan-cv")
async def scan_cv(cv_file: UploadFile = File(...)):
    if config.MOCK:
        return _fixture("scan_cv.json")
    try:
        path = await _read_upload(cv_file)
        try:
            return service.scan(path)
        finally:
            _cleanup(path)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError("SCAN_FAILED", str(e))


@app.post("/cv-suggestions")
async def cv_suggestions(
    cv_file: UploadFile = File(...),
    role_id: str = Form(...),
    level: str = Form("junior"),
):
    if config.MOCK:
        return _fixture("cv_suggestions.json")
    try:
        path = await _read_upload(cv_file)
        try:
            return service.suggestions(path, role_id, config.norm_level(level))
        finally:
            _cleanup(path)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError("SUGGEST_FAILED", str(e))


class ExportReq(BaseModel):
    accepted: list[dict] = []
    format: str = "md"


@app.post("/cv-export")
def cv_export(req: ExportReq):
    try:
        md = service.export_cv(req.accepted)
        return Response(content=md, media_type="text/markdown",
                        headers={"Content-Disposition": "attachment; filename=cv_goi_y.md"})
    except Exception as e:  # noqa: BLE001
        raise AppError("EXPORT_FAILED", str(e))


class RoadmapReq(BaseModel):
    role_id: str
    hours_per_week: int = 5
    skill_ids: list[str]
    level: str = "junior"


@app.post("/roadmap")
def roadmap(req: RoadmapReq):
    if config.MOCK:
        return _fixture("roadmap.json")
    try:
        if req.hours_per_week <= 0:
            raise AppError("BAD_HOURS", "hours_per_week phải lớn hơn 0")
        return service.roadmap(req.role_id, config.norm_level(req.level),
                               req.hours_per_week, req.skill_ids)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError("ROADMAP_FAILED", str(e))


@app.get("/health")
def health():
    return {"status": "ok", "mock": config.MOCK}
