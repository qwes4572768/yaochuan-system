"""保全公司管理系統 - HR 人事管理 API"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import config as app_config
from app.database import init_db
from app.db_schema_fix import ensure_schema
from app.routers import (
    auth,
    employees,
    insurance,
    insurance_brackets,
    documents,
    reports,
    settings,
    rules,
    rate_tables,
    sites,
    rebates,
    monthly_receipts,
    schedules,
    backup_restore,
    accounting,
    patrol,
)
from app.services.backup_job import run_scheduled_backup

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _daily_backup_job():
    try:
        await run_scheduled_backup()
    except Exception:
        logger.exception("每日人事備份排程執行失敗")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # SQLite：啟動時自動補齊缺欄（含 employees 各公司別 pay_mode），避免 no such column
    ensure_schema()
    # 確保自動備份目錄存在（路徑由 backup_job 以 BASE_DIR 為基準解析）
    backup_dir = app_config.settings.backup_dir
    if not backup_dir.is_absolute():
        backup_dir = app_config.BASE_DIR / backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    global _scheduler
    _scheduler = AsyncIOScheduler()
    # 每日自動備份：解析 backup_schedule_time (HH:MM)
    try:
        parts = app_config.settings.backup_schedule_time.strip().split(":")
        hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        _scheduler.add_job(
            _daily_backup_job,
            "cron",
            hour=hour,
            minute=minute,
            id="hr_daily_backup",
            replace_existing=True,
        )
    except (ValueError, IndexError):
        _scheduler.add_job(
            _daily_backup_job,
            "cron",
            hour=0,
            minute=0,
            id="hr_daily_backup",
            replace_existing=True,
        )
    _scheduler.start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(
    title="曜川系統 - HR",
    description="Yaochuan HR system",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yaochuan-system-1.onrender.com",
        "https://yaochuan.com.tw",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(insurance.router)
app.include_router(insurance_brackets.router)
app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(rules.router)
app.include_router(rate_tables.router)
app.include_router(sites.router)
app.include_router(rebates.router)
app.include_router(monthly_receipts.router)
app.include_router(schedules.router)
app.include_router(backup_restore.router)
app.include_router(accounting.router)
app.include_router(patrol.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        raise exc
    detail = str(exc) if exc else "Internal Server Error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


@app.get("/")
def home():
    return {"message": "曜川系統運行中"}


@app.get("/login")
def login_page():
    return FileResponse("static/login.html")
