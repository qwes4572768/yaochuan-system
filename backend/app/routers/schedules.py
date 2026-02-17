"""排班 P0：schedules / schedule_shifts / schedule_assignments CRUD、月統計。"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud, schemas
from app.crud import ScheduleAssignmentNotEligibleError
from app.models import SCHEDULE_STATUSES, SHIFT_CODES, ASSIGNMENT_ROLES

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

RESPONSE_404 = {
    404: {
        "description": "資源不存在",
        "content": {"application/json": {"example": {"detail": "排班表不存在"}}},
    }
}

RESPONSE_409 = {
    409: {
        "description": "業務規則衝突",
        "content": {"application/json": {"example": {"detail": "該員工在此日期不符合指派條件"}}},
    }
}

RESPONSE_422 = {422: {"description": "請求參數或 body 驗證失敗"}}


# ---------- schedules CRUD ----------
@router.get("", response_model=List[schemas.ScheduleRead], summary="排班表列表")
async def list_schedules(
    site_id: Optional[int] = Query(None, description="案場 ID"),
    year: Optional[int] = Query(None, description="年度"),
    month: Optional[int] = Query(None, ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
):
    items = await crud.list_schedules(db, site_id=site_id, year=year, month=month)
    return [schemas.ScheduleRead.model_validate(s) for s in items]


@router.get("/{schedule_id}", response_model=schemas.ScheduleRead, summary="取得單一排班表", responses=RESPONSE_404)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    return schemas.ScheduleRead.model_validate(s)


@router.post("", response_model=schemas.ScheduleRead, status_code=201, summary="新增排班表（某案場某月）", responses=RESPONSE_422)
async def create_schedule(
    data: schemas.ScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    site = await crud.get_site(db, data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="案場不存在")
    if data.status and data.status not in SCHEDULE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status 須為: {list(SCHEDULE_STATUSES)}")
    s = await crud.create_schedule(db, data)
    return schemas.ScheduleRead.model_validate(s)


@router.patch("/{schedule_id}", response_model=schemas.ScheduleRead, summary="更新排班表", responses={**RESPONSE_404, **RESPONSE_422})
async def update_schedule(
    schedule_id: int,
    data: schemas.ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    if data.status is not None and data.status not in SCHEDULE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status 須為: {list(SCHEDULE_STATUSES)}")
    s = await crud.update_schedule(db, s, data)
    return schemas.ScheduleRead.model_validate(s)


@router.delete("/{schedule_id}", status_code=204, summary="刪除排班表（一併刪除班別與指派）", responses=RESPONSE_404)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    await crud.delete_schedule(db, s)


# ---------- schedule_shifts CRUD ----------
@router.get("/{schedule_id}/shifts", response_model=List[schemas.ScheduleShiftRead], summary="排班表底下的班別列表", responses=RESPONSE_404)
async def list_shifts(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    shifts = await crud.list_shifts_by_schedule(db, schedule_id)
    return [schemas.ScheduleShiftRead.model_validate(sh) for sh in shifts]


@router.post("/{schedule_id}/shifts", response_model=schemas.ScheduleShiftRead, status_code=201, summary="新增一筆班別", responses=RESPONSE_404)
async def create_shift(
    schedule_id: int,
    data: schemas.ScheduleShiftCreate,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    if data.shift_code not in SHIFT_CODES:
        raise HTTPException(status_code=400, detail=f"shift_code 須為: {list(SHIFT_CODES)}")
    sh = await crud.create_shift(db, schedule_id, data)
    return schemas.ScheduleShiftRead.model_validate(sh)


@router.post("/{schedule_id}/shifts/batch", response_model=List[schemas.ScheduleShiftRead], summary="批量建立該月班別", responses=RESPONSE_404)
async def batch_create_shifts(
    schedule_id: int,
    data: schemas.ScheduleShiftBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    s = await crud.get_schedule(db, schedule_id)
    if not s:
        raise HTTPException(status_code=404, detail="排班表不存在")
    if data.shift_code not in SHIFT_CODES:
        raise HTTPException(status_code=400, detail=f"shift_code 須為: {list(SHIFT_CODES)}")
    created = await crud.batch_create_shifts_for_month(db, schedule_id, s.year, s.month, data)
    await db.commit()
    return [schemas.ScheduleShiftRead.model_validate(sh) for sh in created]


@router.patch("/{schedule_id}/shifts/{shift_id}", response_model=schemas.ScheduleShiftRead, summary="更新班別", responses=RESPONSE_404)
async def update_shift(
    schedule_id: int,
    shift_id: int,
    data: schemas.ScheduleShiftUpdate,
    db: AsyncSession = Depends(get_db),
):
    sh = await crud.get_shift(db, shift_id)
    if not sh or sh.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="班別不存在")
    if data.shift_code is not None and data.shift_code not in SHIFT_CODES:
        raise HTTPException(status_code=400, detail=f"shift_code 須為: {list(SHIFT_CODES)}")
    sh = await crud.update_shift(db, sh, data)
    return schemas.ScheduleShiftRead.model_validate(sh)


@router.delete("/{schedule_id}/shifts/{shift_id}", status_code=204, summary="刪除班別", responses=RESPONSE_404)
async def delete_shift(
    schedule_id: int,
    shift_id: int,
    db: AsyncSession = Depends(get_db),
):
    sh = await crud.get_shift(db, shift_id)
    if not sh or sh.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="班別不存在")
    await crud.delete_shift(db, sh)


# ---------- schedule_assignments CRUD ----------
@router.get("/{schedule_id}/shifts/{shift_id}/assignments", response_model=List[schemas.ScheduleAssignmentWithEmployee], summary="班別底下的人員指派", responses=RESPONSE_404)
async def list_shift_assignments(
    schedule_id: int,
    shift_id: int,
    db: AsyncSession = Depends(get_db),
):
    sh = await crud.get_shift(db, shift_id)
    if not sh or sh.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="班別不存在")
    assignments = await crud.list_assignments_by_shift(db, shift_id, load_employee=True)
    out = []
    for a in assignments:
        d = schemas.ScheduleAssignmentRead.model_validate(a).model_dump()
        d["employee_name"] = a.employee.name if a.employee else None
        out.append(schemas.ScheduleAssignmentWithEmployee(**d))
    return out


@router.post("/{schedule_id}/shifts/{shift_id}/assignments", response_model=schemas.ScheduleAssignmentRead, status_code=201, summary="指派員工到班別", responses={**RESPONSE_404, **RESPONSE_409})
async def create_schedule_assignment(
    schedule_id: int,
    shift_id: int,
    data: schemas.ScheduleAssignmentCreate,
    db: AsyncSession = Depends(get_db),
):
    sh = await crud.get_shift(db, shift_id)
    if not sh or sh.schedule_id != schedule_id:
        raise HTTPException(status_code=404, detail="班別不存在")
    emp = await crud.get_employee(db, data.employee_id, load_dependents=False)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    if data.role and data.role not in ASSIGNMENT_ROLES:
        raise HTTPException(status_code=400, detail=f"role 須為: {list(ASSIGNMENT_ROLES)}")
    try:
        a = await crud.create_schedule_assignment(db, shift_id, data)
    except ScheduleAssignmentNotEligibleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return schemas.ScheduleAssignmentRead.model_validate(a)


@router.patch("/{schedule_id}/shifts/{shift_id}/assignments/{assignment_id}", response_model=schemas.ScheduleAssignmentRead, summary="更新指派", responses=RESPONSE_404)
async def update_schedule_assignment(
    schedule_id: int,
    shift_id: int,
    assignment_id: int,
    data: schemas.ScheduleAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    a = await crud.get_schedule_assignment(db, assignment_id)
    if not a or a.shift_id != shift_id or (a.shift and a.shift.schedule_id != schedule_id):
        raise HTTPException(status_code=404, detail="指派不存在")
    if data.role is not None and data.role not in ASSIGNMENT_ROLES:
        raise HTTPException(status_code=400, detail=f"role 須為: {list(ASSIGNMENT_ROLES)}")
    a = await crud.update_schedule_assignment(db, a, data)
    return schemas.ScheduleAssignmentRead.model_validate(a)


@router.delete("/{schedule_id}/shifts/{shift_id}/assignments/{assignment_id}", status_code=204, summary="移除指派", responses=RESPONSE_404)
async def delete_schedule_assignment(
    schedule_id: int,
    shift_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
):
    a = await crud.get_schedule_assignment(db, assignment_id)
    if not a or a.shift_id != shift_id or (a.shift and a.shift.schedule_id != schedule_id):
        raise HTTPException(status_code=404, detail="指派不存在")
    await crud.delete_schedule_assignment(db, a)


# ---------- 月統計 ----------
@router.get("/stats/monthly", response_model=List[schemas.EmployeeMonthlyShiftStats], summary="產出員工某月排班統計（總班數、總工時、夜班數）")
async def get_monthly_shift_stats(
    year_month: int = Query(..., description="西元年月，如 202501"),
    employee_id: Optional[int] = Query(None, description="篩選單一員工"),
    db: AsyncSession = Depends(get_db),
):
    rows = await crud.get_employee_monthly_shift_stats(db, year_month, employee_id=employee_id)
    return [schemas.EmployeeMonthlyShiftStats(**r) for r in rows]
