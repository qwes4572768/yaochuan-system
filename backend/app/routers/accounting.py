"""傻瓜會計 API：保全核心計算（上傳時數檔 → 計算薪資）、歷史查詢、Excel 匯出。"""
import io
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud
from app.accounting.security_payroll_service import (
    parse_security_hours_file,
    SecurityPayrollCalculator,
    compute_test_rounding,
)
from app.accounting.payroll_export import build_payroll_excel, build_payroll_excel_grouped
from app.utils.http_headers import build_content_disposition

router = APIRouter(prefix="/api/accounting", tags=["accounting"])

ALLOWED_EXTENSIONS = {"xlsx", "xls", "ods"}
# 計算類型：目前僅實作 security；預留 property, smith, cleaning
PAYROLL_TYPES = {"security", "property", "smith", "cleaning"}
EMPLOYEE_LOOKUP_TYPES = {"security", "property", "smith", "lixiang", "cleaning"}


def _payroll_type_label(payroll_type: str) -> str:
    return {
        "security": "保全",
        "property": "物業",
        "smith": "史密斯",
        "cleaning": "清潔",
    }.get((payroll_type or "").strip().lower(), "薪資")


@router.post("/security-payroll/upload")
async def security_payroll_upload(
    file: UploadFile = File(...),
    year: int | None = Form(None),
    month: int | None = Form(None),
    type: str | None = Form(None, alias="type"),
    payroll_type: str | None = Form(None),
    extra_payroll_types: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    上傳時數檔案（xlsx / xls / ods），必須帶入 year, month, type。
    解析後驗證並計算每人每月工時與薪資（依 type 套用對應規則），回傳結果含 year, month, type。
    同年月重複上傳會先刪除該月份該類別舊資料再寫入（覆蓋）。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="請選擇檔案")
    # 強制要求 year / month，且 month 1-12；缺一即 400 中文提示
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="請先選擇年份與月份再上傳計算")
    try:
        y, m = int(year), int(month)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="請先選擇年份與月份再上傳計算")
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="請先選擇年份與月份再上傳計算")
    payroll_type_value = (payroll_type or type or "").strip().lower()
    payroll_type = payroll_type_value
    if not payroll_type or payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效，請傳入 type=security/property/smith/cleaning")
    dedup_extra_types: list[str] = []
    if extra_payroll_types:
        try:
            parsed = json.loads(extra_payroll_types)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="extra_payroll_types 格式錯誤，需為字串陣列 JSON")
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="extra_payroll_types 格式錯誤，需為字串陣列 JSON")
        seen = set()
        for item in parsed:
            key = str(item or "").strip().lower()
            if (
                not key
                or key == payroll_type
                or key in seen
                or key not in EMPLOYEE_LOOKUP_TYPES
            ):
                continue
            seen.add(key)
            dedup_extra_types.append(key)
    # 年範圍：當前 ±2（由前端控制，後端僅做合理範圍）
    from datetime import date
    this_year = date.today().year
    if y < this_year - 2 or y > this_year + 2:
        raise HTTPException(status_code=400, detail="年份超出允許範圍")

    ext = file.filename.lower().split(".")[-1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="僅支援 xlsx / xls / ods 格式")

    content = await file.read()
    try:
        rows, parse_errors = parse_security_hours_file(content, file.filename or "", year=y, month=m)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    calculator = SecurityPayrollCalculator(db)
    results, calc_errors, debug = await calculator.validate_and_calculate(
        rows,
        year=y,
        month=m,
        payroll_type=payroll_type,
        extra_payroll_types=dedup_extra_types,
    )
    errors = [{"type": "parse_error", "message": msg} for msg in parse_errors] + calc_errors

    # 同年月同類型：先刪除舊資料再插入，同一 transaction 內完成（覆蓋，不累積）；失敗會 rollback
    deleted_before_insert = await crud.delete_payroll_results_for_period(db, y, m, payroll_type)
    if results:
        await crud.save_payroll_results(db, y, m, payroll_type, results)

    out = {
        "results": results,
        "errors": errors,
        "deleted_before_insert": deleted_before_insert,
        "inserted": len(results),
    }
    if debug is not None:
        out["debug"] = debug
    return out


@router.get("/security-payroll/test-rounding")
def security_payroll_test_rounding():
    """
    內建測試：每日先 round 再加總。固定 daily_rate=10875, hourly=906.25, 30天各11時。
    預期 gross=299062.50。回傳 JSON 供驗證。
    """
    return compute_test_rounding()


# ---------- 歷史查詢 ----------


@router.get("/security-payroll/history")
async def security_payroll_history(
    year: int = Query(..., description="西元年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    payroll_type: str = Query("security", description="計算類型"),
    db: AsyncSession = Depends(get_db),
):
    """
    依類別/年/月查詢已存檔的薪資結果。
    回傳 results 與 summary（total_gross, total_net, total_deductions, row_count）。
    """
    if payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效")
    results = await crud.get_payroll_results_for_period(db, year, month, payroll_type)
    enriched_results, stats = await crud.enrich_history_records(db, results)
    total_gross = sum((r.get("gross_salary") or r.get("total_salary") or 0) for r in results)
    total_net = sum((r.get("net_salary") or r.get("total_salary") or 0) for r in results)
    total_deductions = sum((r.get("deductions_total") or 0) for r in results)
    return {
        "year": year,
        "month": month,
        "payroll_type": payroll_type,
        "results": enriched_results,
        "summary": {
            "total_gross": round(total_gross, 0),
            "total_net": round(total_net, 0),
            "total_deductions": round(total_deductions, 0),
            "row_count": len(results),
        },
        "stats": stats,
    }


@router.get("/security-payroll/history-months")
async def security_payroll_history_months(
    payroll_type: str = Query("security", description="計算類型"),
    db: AsyncSession = Depends(get_db),
):
    """回傳已存檔的 (year, month) 列表，供前端下拉選單。"""
    if payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效")
    months = await crud.get_payroll_history_months(db, payroll_type)
    return {"payroll_type": payroll_type, "months": months}


# 提供前端下拉使用：只回傳 DB 實際存在的 distinct year/month
@router.get("/security-payroll/months")
async def security_payroll_months(
    payroll_type: str = Query("security", description="計算類型"),
    db: AsyncSession = Depends(get_db),
):
    """
    回傳資料庫真實存在的歷史月份（distinct year/month，依新到舊）。
    只由 DB 結果決定，避免前端硬塞不存在月份。
    """
    if payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效")
    rows = await crud.get_payroll_history_months(db, payroll_type)
    # 依需求回傳字串清單格式：YYYY-MM
    months = [f"{r['year']}-{int(r['month']):02d}" for r in rows]
    return {"months": months}


@router.delete("/security-payroll/history")
async def security_payroll_history_delete(
    year: int = Query(..., description="西元年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    payroll_type: str = Query("security", description="計算類型"),
    db: AsyncSession = Depends(get_db),
):
    """
    安全刪除指定年月/類型的歷史資料。
    僅刪除 accounting_payroll_results WHERE year=:year AND month=:month AND type=:payroll_type。
    """
    if payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效")
    deleted_count = await crud.delete_payroll_results_for_period(db, year, month, payroll_type)
    return {"deleted_count": deleted_count}


# ---------- 一鍵清除指定年月（安全刪除，僅刪該 year/month/type） ----------


@router.post("/security-payroll/delete")
async def security_payroll_delete(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    一鍵清除指定年/月/類型的薪資結果。僅刪除 accounting_payroll_results 符合條件的列，
    不 drop table、不重建 DB、不刪其他月份。同一 transaction：先 COUNT 再 DELETE。
    回傳 deleted_count, year, month, type。
    """
    year = body.get("year")
    month = body.get("month")
    payroll_type_raw = body.get("payroll_type", "security")
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="請提供 year 與 month")
    try:
        y, m = int(year), int(month)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="year、month 須為數字")
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="月份須為 1～12")
    payroll_type = (payroll_type_raw or "").strip().lower()
    if not payroll_type or payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="payroll_type 須為 security / property / smith / cleaning")
    # 西元年，不可混用民國
    if y < 2000 or y > 2100:
        raise HTTPException(status_code=400, detail="year 須為西元年（2000～2100）")

    # 同一 transaction：先查筆數，再刪除（僅刪 WHERE year=y AND month=m AND type=payroll_type）
    count_before = await crud.count_payroll_results_for_period(db, y, m, payroll_type)
    deleted_count = await crud.delete_payroll_results_for_period(db, y, m, payroll_type)

    return {
        "deleted_count": deleted_count,
        "count_before": count_before,
        "year": y,
        "month": m,
        "type": payroll_type,
    }


@router.post("/security-payroll/admin/delete")
async def security_payroll_admin_delete(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    管理用刪除：需 confirm=DELETE，僅刪除指定 year/month/type。
    同一 transaction：先 COUNT 再 DELETE。
    """
    year = body.get("year")
    month = body.get("month")
    payroll_type_raw = body.get("payroll_type", "security")
    confirm = body.get("confirm")

    if confirm != "DELETE":
        raise HTTPException(status_code=400, detail="請帶入 confirm=DELETE 才能執行刪除")
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="請提供 year 與 month")
    try:
        y, m = int(year), int(month)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="year、month 須為數字")
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="月份須為 1～12")
    payroll_type = (payroll_type_raw or "").strip().lower()
    if not payroll_type or payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="payroll_type 須為 security / property / smith / cleaning")

    # 嚴格匹配 year/month/type，不刪其他月份
    await crud.count_payroll_results_for_period(db, y, m, payroll_type)
    deleted_count = await crud.delete_payroll_results_for_period(db, y, m, payroll_type)
    return {"deleted_count": deleted_count}


# ---------- Excel 匯出 ----------


@router.post("/security-payroll/export")
async def security_payroll_export_post(
    body: dict,
):
    """
    匯出「當次計算結果」為 Excel（尚未入庫也可匯出）。
    body: { year, month, payroll_type, results: [...] }；檔名依 body.year / body.month。
    """
    year = body.get("year")
    month = body.get("month")
    payroll_type = body.get("payroll_type", "security")
    results = body.get("results") or []
    if not isinstance(results, list):
        raise HTTPException(status_code=400, detail="results 須為陣列")
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="請提供 year 與 month")
    try:
        y, m = int(year), int(month)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="year、month 須為數字")
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="月份須為 1～12")
    label = f"{y}年{str(m).zfill(2)}月"
    sheet_name = f"{_payroll_type_label(payroll_type)}薪資_{label}"
    content = build_payroll_excel(results, sheet_name=sheet_name)
    ascii_name = f"{payroll_type}_payroll_{y}_{m:02d}.xlsx"
    unicode_name = f"{_payroll_type_label(payroll_type)}核薪_{y}_{m:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(ascii_name, unicode_name)},
    )


@router.get("/security-payroll/export")
async def security_payroll_export_get(
    year: int = Query(..., description="西元年"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    payroll_type: str = Query("security", description="計算類型"),
    db: AsyncSession = Depends(get_db),
):
    """依年/月從資料庫匯出歷史薪資結果為 Excel。"""
    if payroll_type not in PAYROLL_TYPES:
        raise HTTPException(status_code=400, detail="計算類型無效")
    results = await crud.get_payroll_results_for_period(db, year, month, payroll_type)
    if not results:
        raise HTTPException(status_code=404, detail="該月份尚無存檔資料")
    enriched_results, stats = await crud.enrich_history_records(db, results)
    content = build_payroll_excel_grouped(enriched_results, stats)
    ascii_name = f"{payroll_type}_payroll_{year}_{month:02d}.xlsx"
    unicode_name = f"{_payroll_type_label(payroll_type)}核薪_{year}_{month:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(ascii_name, unicode_name)},
    )
