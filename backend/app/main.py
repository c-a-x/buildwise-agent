from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import audit, auth, dashboard, green, health, knowledge, modules, projects, quality, reports, safety, stats, users, wellbeing, work_orders, worker_care
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.utils.ids import new_id


configure_logging()
logger = logging.getLogger("buildwise")

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = f"REQ-{uuid4().hex[:12].upper()}"
    return await call_next(request)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.message, "error": {"code": exc.code, "details": exc.details}, "request_id": getattr(request.state, "request_id", new_id("REQ"))})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "message": "参数校验失败", "error": {"code": "VALIDATION_ERROR", "details": exc.errors()}, "request_id": getattr(request.state, "request_id", new_id("REQ"))})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(status_code=500, content={"success": False, "message": "服务器内部错误", "error": {"code": "INTERNAL_ERROR", "details": None}, "request_id": getattr(request.state, "request_id", new_id("REQ"))})


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "api_prefix": settings.api_prefix}


for endpoint in (health, modules, auth, users, projects, dashboard, safety, work_orders, worker_care, wellbeing, reports, knowledge, quality, green, stats, audit):
    app.include_router(endpoint.router, prefix=settings.api_prefix)
app.mount("/storage", StaticFiles(directory=str(settings.storage_dir)), name="storage")
