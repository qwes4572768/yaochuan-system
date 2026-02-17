"""案場管理 API：案場 CRUD、案場-員工指派（多對多）、軟刪除（移除案場）。"""
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app import crud, schemas
from app.crud import AssignmentPeriodOverlapError, SiteInactiveError
from app.schemas import SiteListItem

router = APIRouter(prefix="/api/sites", tags=["sites"])

# 錯誤回傳格式：FastAPI 預設 { "detail": "訊息" }；404/409/422 皆以 detail 回傳中文
RESPONSE_404 = {404: {"description": "資源不存在", "content": {"application/json": {"example": {"detail": "案場不存在"}}}}}
RESPONSE_409 = {409: {"description": "衝突（如重複指派、期間重疊）", "content": {"application/json": {"example": {"detail": "該員工已指派至此案場"}}}}}
RESPONSE_422 = {422: {"description": "請求參數或 body 驗證失敗", "content": {"application/json": {"example": {"detail": [{"loc": ["body", "field"], "msg": "field required", "type": "value_error.missing"}]}}}}}


# ---------- 案場 CRUD ----------
def _site_to_list_item(site, receipt_map: dict, current_ym: str):
    """將 Site ORM 轉成 SiteListItem，含 days_to_expire、status、本月應收、本月是否入帳。"""
    today = date.today()
    remind_days = getattr(site, "remind_days", None) or 30
    contract_end = getattr(site, "contract_end", None)
    days_to_expire = None
    status_val = "normal"
    if contract_end is not None:
        delta = (contract_end - today).days
        days_to_expire = delta
        if delta < 0:
            status_val = "expired"
        elif delta <= remind_days:
            status_val = "expiring"
    receipt = receipt_map.get(site.id)
    current_month_expected = getattr(site, "monthly_fee_incl_tax", None)
    if receipt and getattr(receipt, "expected_amount", None) is not None:
        current_month_expected = receipt.expected_amount
    current_month_received = receipt.is_received if receipt else False
    is_active = getattr(site, "is_active", True)
    is_archived = getattr(site, "is_archived", False)
    # 已移除案場在列表狀態欄顯示「已移除」；歷史案場顯示「已到期」
    if not is_active:
        status_val = "inactive" if not is_archived else "expired"
    d = {
        "id": site.id,
        "name": site.name,
        "address": site.address,
        "site_type": getattr(site, "site_type", None),
        "service_types": getattr(site, "service_types", None),
        "contract_start": getattr(site, "contract_start", None),
        "contract_end": contract_end,
        "monthly_fee_excl_tax": getattr(site, "monthly_fee_excl_tax", None),
        "monthly_fee_incl_tax": getattr(site, "monthly_fee_incl_tax", None),
        "invoice_due_day": getattr(site, "invoice_due_day", None),
        "payment_due_day": getattr(site, "payment_due_day", None),
        "client_name": site.client_name,
        "customer_name": getattr(site, "customer_name", None),
        "days_to_expire": days_to_expire,
        "status": status_val,
        "current_month_expected_amount": current_month_expected,
        "current_month_received": current_month_received,
        "created_at": site.created_at,
        "updated_at": site.updated_at,
        "is_active": is_active,
        "is_archived": is_archived,
    }
    return SiteListItem(**d)


@router.get(
    "",
    response_model=schemas.SiteListResponse,
    summary="案場列表（分頁與搜尋，含到期狀態與本月應收）",
    responses={**RESPONSE_422},
)
async def list_sites(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=500, description="每頁筆數"),
    load_assignments: bool = Query(False, description="是否載入指派員工"),
    q: str | None = Query(None, description="關鍵字：案場名稱、客戶名稱、案場地址（部分符合）"),
    payment_method: str | None = Query(None, description="收款方式：transfer / cash / check"),
    is_841: bool | None = Query(None, alias="is_841", description="是否 84-1 案場"),
    contract_active: bool | None = Query(None, description="合約是否有效中（合約結束日為空或 >= 今日）"),
    site_type: str | None = Query(None, description="案場類型：community / factory"),
    service_type: str | None = Query(None, description="服務類型篩選（單一，部分符合）"),
    status: str | None = Query(None, description="狀態：normal / expiring / expired"),
    include_inactive: bool = Query(False, description="是否含已移除案場（預設僅有效）"),
    db: AsyncSession = Depends(get_db),
):
    await crud.run_expired_archive_check(db)
    sites, total = await crud.list_sites(
        db,
        page=page,
        page_size=page_size,
        load_assignments=load_assignments,
        q=q,
        payment_method=payment_method,
        is_84_1=is_841,
        contract_active=contract_active,
        site_type=site_type,
        service_types=service_type,
        status=status,
        include_inactive=include_inactive,
    )
    current_ym = date.today().strftime("%Y-%m")
    site_ids = [s.id for s in sites]
    receipts = await crud.get_monthly_receipts_for_sites(db, site_ids, current_ym)
    receipt_map = {r.site_id: r for r in receipts}
    items = [_site_to_list_item(s, receipt_map, current_ym) for s in sites]
    return schemas.SiteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/history",
    response_model=schemas.SiteListResponse,
    summary="案場歷史紀錄（到期未續約，不含手動移除）",
    responses={**RESPONSE_422},
)
async def list_sites_history(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=500, description="每頁筆數"),
    q: str | None = Query(None, description="關鍵字：案場名稱、客戶名稱、案場地址"),
    status: str | None = Query(None, description="狀態篩選：normal / expiring / expired"),
    db: AsyncSession = Depends(get_db),
):
    sites, total = await crud.list_sites_history(
        db, page=page, page_size=page_size, q=q, status=status
    )
    current_ym = date.today().strftime("%Y-%m")
    site_ids = [s.id for s in sites]
    receipts = await crud.get_monthly_receipts_for_sites(db, site_ids, current_ym)
    receipt_map = {r.site_id: r for r in receipts}
    items = [_site_to_list_item(s, receipt_map, current_ym) for s in sites]
    return schemas.SiteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/by-employee/{employee_id}/assignments",
    response_model=List[schemas.SiteAssignmentWithSite],
    summary="查詢某員工被指派的案場",
    responses={**RESPONSE_404},
)
async def list_employee_site_assignments(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    emp = await crud.get_employee(db, employee_id, load_dependents=False)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    assignments = await crud.list_assignments_by_employee(db, employee_id, load_site=True)
    out = []
    for a in assignments:
        d = schemas.SiteAssignmentRead.model_validate(a).model_dump()
        d["site_name"] = a.site.name if a.site else None
        d["site_client_name"] = a.site.client_name if a.site else None
        out.append(schemas.SiteAssignmentWithSite(**d))
    return out


# ---------- 案場回饋 rebates（路徑須在 /{site_id} 之前）----------
@router.get(
    "/{site_id}/rebates",
    response_model=List[schemas.SiteRebateRead],
    summary="取得案場回饋列表",
    responses={**RESPONSE_404},
)
async def list_site_rebates(
    site_id: int,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    items = await crud.list_rebates_by_site(db, site_id)
    return [schemas.SiteRebateRead.model_validate(r) for r in items]


@router.post(
    "/{site_id}/rebates",
    response_model=schemas.SiteRebateRead,
    status_code=201,
    summary="新增案場回饋",
    responses={**RESPONSE_404, **RESPONSE_422},
)
async def create_site_rebate(
    site_id: int,
    data: schemas.SiteRebateCreate,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    rebate = await crud.create_rebate(db, site_id, data)
    return schemas.SiteRebateRead.model_validate(rebate)


# ---------- 案場每月入帳 monthly-receipts（路徑須在 /{site_id} 之前）----------
@router.get(
    "/{site_id}/monthly-receipts",
    response_model=List[schemas.SiteMonthlyReceiptRead],
    summary="取得案場每月入帳列表（可篩選年度）",
    responses={**RESPONSE_404},
)
async def list_site_monthly_receipts(
    site_id: int,
    year: int | None = Query(None, description="篩選年度，例如 2026"),
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    items = await crud.list_monthly_receipts_by_site(db, site_id, year=year)
    return [schemas.SiteMonthlyReceiptRead.model_validate(r) for r in items]


@router.post(
    "/{site_id}/monthly-receipts",
    response_model=List[schemas.SiteMonthlyReceiptRead],
    status_code=201,
    summary="新增每月入帳（單筆或一鍵產生全年月份）",
    responses={**RESPONSE_404, **RESPONSE_422},
)
async def create_site_monthly_receipts(
    site_id: int,
    data: schemas.SiteMonthlyReceiptCreate | schemas.SiteMonthlyReceiptBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    default_expected = getattr(site, "monthly_fee_incl_tax", None)
    if isinstance(data, schemas.SiteMonthlyReceiptBatchCreate):
        created = await crud.create_monthly_receipts_for_year(db, site_id, data.year, default_expected)
        return [schemas.SiteMonthlyReceiptRead.model_validate(r) for r in created]
    created_one = await crud.create_monthly_receipt(db, site_id, data, default_expected=default_expected)
    return [schemas.SiteMonthlyReceiptRead.model_validate(created_one)]


@router.get(
    "/{site_id}",
    response_model=schemas.SiteRead,
    summary="取得單一案場",
    responses={**RESPONSE_404},
)
async def get_site(
    site_id: int,
    load_assignments: bool = Query(False, description="是否載入指派員工"),
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id, load_assignments=load_assignments)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    return schemas.SiteRead.model_validate(site)


@router.post(
    "",
    response_model=schemas.SiteRead,
    status_code=201,
    summary="新增案場",
    responses={**RESPONSE_422},
)
async def create_site(data: schemas.SiteCreate, db: AsyncSession = Depends(get_db)):
    site = await crud.create_site(db, data)
    return schemas.SiteRead.model_validate(site)


@router.patch(
    "/{site_id}",
    response_model=schemas.SiteRead,
    summary="更新案場",
    responses={**RESPONSE_404, **RESPONSE_422},
)
async def update_site(
    site_id: int,
    data: schemas.SiteUpdate,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    try:
        site = await crud.update_site(db, site, data)
    except SiteInactiveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return schemas.SiteRead.model_validate(site)


@router.delete(
    "/{site_id}",
    status_code=204,
    summary="實體刪除案場（內部用，一般請使用 POST /deactivate 軟刪除）",
    responses={**RESPONSE_404},
)
async def delete_site(site_id: int, db: AsyncSession = Depends(get_db)):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    await crud.delete_site(db, site)


@router.post(
    "/{site_id}/deactivate",
    response_model=schemas.SiteRead,
    summary="移除案場（軟刪除，僅管理員）",
    responses={**RESPONSE_404, 403: {"description": "僅管理員可執行移除"}},
)
async def deactivate_site(
    site_id: int,
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
):
    """軟刪除：設定 is_active=False、deactivated_at、deactivated_reason=manual。須帶 X-Admin-Token。"""
    if not settings.admin_backup_token or x_admin_token != settings.admin_backup_token:
        raise HTTPException(status_code=403, detail="僅管理員可執行移除案場，請提供正確的 X-Admin-Token")
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    if not getattr(site, "is_active", True):
        raise HTTPException(status_code=400, detail="此案場已移除")
    site = await crud.deactivate_site(db, site, reason="manual")
    return schemas.SiteRead.model_validate(site)


# ---------- 案場底下的員工指派 ----------
@router.get(
    "/{site_id}/assignments",
    response_model=List[schemas.SiteAssignmentWithEmployee],
    summary="案場底下的指派列表（含員工姓名）",
    responses={**RESPONSE_404},
)
async def list_site_assignments(
    site_id: int,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    assignments = await crud.list_assignments_by_site(db, site_id, load_employee=True)
    out = []
    for a in assignments:
        d = schemas.SiteAssignmentRead.model_validate(a).model_dump()
        d["employee_name"] = a.employee.name if a.employee else None
        out.append(schemas.SiteAssignmentWithEmployee(**d))
    return out


@router.post(
    "/{site_id}/assignments",
    response_model=schemas.SiteAssignmentRead,
    status_code=201,
    summary="新增指派（同一 site_id + employee_id 僅一筆；期間不可重疊）",
    responses={**RESPONSE_404, **RESPONSE_409, **RESPONSE_422},
)
async def add_site_assignment(
    site_id: int,
    data: schemas.SiteAssignmentCreate,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    emp = await crud.get_employee(db, data.employee_id, load_dependents=False)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    try:
        a = await crud.create_assignment(db, site_id, data)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="該員工已指派至此案場")
    except AssignmentPeriodOverlapError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return schemas.SiteAssignmentRead.model_validate(a)


@router.patch(
    "/{site_id}/assignments/{assignment_id}",
    response_model=schemas.SiteAssignmentRead,
    summary="更新指派（期間不可與同案場同員工其他指派重疊）",
    responses={**RESPONSE_404, **RESPONSE_409, **RESPONSE_422},
)
async def update_site_assignment(
    site_id: int,
    assignment_id: int,
    data: schemas.SiteAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    a = await crud.get_assignment(db, assignment_id)
    if not a or a.site_id != site_id:
        raise HTTPException(status_code=404, detail="指派紀錄不存在")
    try:
        a = await crud.update_assignment(db, a, data)
    except AssignmentPeriodOverlapError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return schemas.SiteAssignmentRead.model_validate(a)


@router.delete(
    "/{site_id}/assignments/{assignment_id}",
    status_code=204,
    summary="移除指派",
    responses={**RESPONSE_404},
)
async def remove_site_assignment(
    site_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
):
    a = await crud.get_assignment(db, assignment_id)
    if not a or a.site_id != site_id:
        raise HTTPException(status_code=404, detail="指派紀錄不存在")
    await crud.delete_assignment(db, a)
