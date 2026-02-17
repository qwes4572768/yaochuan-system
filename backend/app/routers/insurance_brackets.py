"""勞健保級距表匯入（權威資料）：上傳 Excel、查表試算、下載原檔。"""
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.database import get_db
from app.config import settings
from app.crud import (
    get_latest_bracket_import,
    get_bracket_by_level,
    create_bracket_import,
    get_employee,
)
from app.schemas import ItemBreakdown, InsuranceEstimateResponse
from app.services.bracket_excel_parser import parse_bracket_excel

router = APIRouter(prefix="/api/insurance-brackets", tags=["insurance-brackets"])
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BRACKET_UPLOAD_DIR = "bracket_imports"


def _bracket_upload_base() -> Path:
    base = settings.upload_dir
    if not base.is_absolute():
        base = Path(__file__).resolve().parents[2] / base
    return base / BRACKET_UPLOAD_DIR


@router.post("/import", summary="上傳級距表 Excel，解析後存入 DB")
async def import_bracket_excel(
    file: UploadFile = File(..., description="勞健保級距表 .xlsx（欄位：級距、勞保公司/員工、健保公司/員工、職災、勞退6%、團保）"),
    version: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="僅接受 .xlsx 檔案")
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案不得超過 10MB")

    parse_result = parse_bracket_excel(raw)
    rows = parse_result.get("rows") or []
    errors = parse_result.get("errors") or []

    if not rows:
        msg = next((e.get("message") for e in errors if e.get("message")), "無有效資料列，請確認 B 欄為級距金額（數字）")
        raise HTTPException(status_code=400, detail=msg)

    # 建立匯入主檔與明細（尚未 commit）
    imp = await create_bracket_import(
        db,
        file_name=file.filename,
        file_path=None,
        row_count=len(rows),
        version=version or file.filename,
        brackets=rows,
    )
    # 儲存原檔供下載
    base = _bracket_upload_base()
    base.mkdir(parents=True, exist_ok=True)
    import_dir = base / str(imp.id)
    import_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ") or "import.xlsx"
    if not safe_name.lower().endswith(".xlsx"):
        safe_name += ".xlsx"
    file_path = import_dir / safe_name
    file_path.write_bytes(raw)
    imp.file_path = f"{BRACKET_UPLOAD_DIR}/{imp.id}/{safe_name}"
    await db.commit()
    await db.refresh(imp)
    resp = {
        "id": imp.id,
        "file_name": imp.file_name,
        "row_count": imp.row_count,
        "version": imp.version,
        "imported_at": imp.imported_at.isoformat() if imp.imported_at else None,
        "message": "匯入成功，試算將以此級距表為依據",
    }
    if errors:
        resp["warnings"] = errors[:20]
    return resp


@router.get("/latest", summary="取得最近一次匯入資訊（時間、筆數、檔名）")
async def get_latest_import(db: AsyncSession = Depends(get_db)):
    imp = await get_latest_bracket_import(db)
    if not imp:
        return {
            "has_import": False,
            "message": "尚未匯入級距表，請先上傳 Excel",
        }
    return {
        "has_import": True,
        "id": imp.id,
        "file_name": imp.file_name,
        "row_count": imp.row_count,
        "version": imp.version,
        "imported_at": imp.imported_at.isoformat() if imp.imported_at else None,
        "file_path": imp.file_path,
    }


@router.get("/latest/file", summary="下載最近一次匯入的 Excel 原檔")
async def download_latest_import_file(db: AsyncSession = Depends(get_db)):
    imp = await get_latest_bracket_import(db)
    if not imp or not imp.file_path:
        raise HTTPException(status_code=404, detail="尚無匯入檔案可下載")
    full = Path(settings.upload_dir) / imp.file_path
    full = full.resolve()
    if not full.is_file():
        raise HTTPException(status_code=404, detail="原檔不存在")
    return FileResponse(
        path=str(full),
        filename=imp.file_name or "bracket_import.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/estimate", summary="依投保級距查表試算（唯一依據：級距表）")
async def estimate_by_bracket(
    insured_salary_level: int,
    db: AsyncSession = Depends(get_db),
):
    """以級距表為唯一依據：依投保級距查表，回傳公司/員工/合計；找不到級距時回傳明確錯誤。"""
    imp = await get_latest_bracket_import(db)
    if not imp or not imp.brackets:
        raise HTTPException(
            status_code=400,
            detail="級距表尚未匯入，請先至「級距表匯入」上傳 Excel 後再試算",
        )
    bracket = await get_bracket_by_level(db, imp.id, insured_salary_level)
    if not bracket:
        raise HTTPException(
            status_code=400,
            detail=f"級距表找不到此級距（{insured_salary_level}），請先匯入最新版 Excel 或補齊級距",
        )
    labor_employer = bracket.labor_employer
    labor_employee = bracket.labor_employee
    health_employer = bracket.health_employer
    health_employee = bracket.health_employee
    occ = bracket.occupational_accident
    pension = bracket.labor_pension
    # 團保不從 Excel 讀取，固定月費由 config，全由員工負擔
    group_employer = Decimal("0")
    group_employee = Decimal(str(settings.group_insurance_monthly_fee))
    group_total = group_employee
    total_employer = labor_employer + health_employer + occ + pension + group_employer
    total_employee = labor_employee + health_employee + group_employee
    total = total_employer + total_employee
    imported_at_str = imp.imported_at.strftime("%Y-%m-%d %H:%M") if imp.imported_at else ""
    return {
        "insured_salary_level": insured_salary_level,
        "labor_insurance": ItemBreakdown(
            name="勞保", employer=labor_employer, employee=labor_employee, total=labor_employer + labor_employee
        ),
        "health_insurance": ItemBreakdown(
            name="健保", employer=health_employer, employee=health_employee, total=health_employer + health_employee
        ),
        "occupational_accident": ItemBreakdown(name="職災", employer=occ, employee=Decimal("0"), total=occ),
        "labor_pension": ItemBreakdown(name="勞退6%", employer=pension, employee=Decimal("0"), total=pension),
        "group_insurance": ItemBreakdown(name="團保", employer=group_employer, employee=group_employee, total=group_total),
        "total_employer": total_employer,
        "total_employee": total_employee,
        "total": total,
        "dependent_count": 0,
        "from_bracket_table": True,
        "bracket_source": {
            "file_name": imp.file_name,
            "imported_at": imported_at_str,
        },
    }
