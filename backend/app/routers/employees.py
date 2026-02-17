"""員工與眷屬 CRUD API；敏感欄位預設遮罩，可選 ?reveal_sensitive=1 取得明文。employee_id 永久不變。"""
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud, schemas
from app.sensitive import employee_to_read_dict, dependent_to_read_dict

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _reveal(reveal_sensitive: bool) -> bool:
    return bool(reveal_sensitive)


@router.get("", response_model=List[schemas.EmployeeRead])
async def list_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="搜尋姓名（部分符合）"),
    registration_type: Optional[str] = Query(None, description="登載身份篩選：security=保全、property=物業、smith=史密斯、lixiang=立翔人力，不傳則全部"),
    reveal_sensitive: bool = Query(False, description="是否回傳敏感欄位明文"),
    db: AsyncSession = Depends(get_db),
):
    employees = await crud.list_employees(db, skip=skip, limit=limit, search=search, registration_type=registration_type, load_dependents=True)
    reveal = _reveal(reveal_sensitive)
    return [schemas.EmployeeRead(**employee_to_read_dict(e, reveal)) for e in employees]


@router.get("/{employee_id}", response_model=schemas.EmployeeRead)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    """單筆查詢（編輯用）：一律回傳完整 national_id / reg_address / live_address，不遮罩。"""
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    return schemas.EmployeeRead(**employee_to_read_dict(emp, reveal_sensitive=True))


@router.post("", response_model=schemas.EmployeeRead, status_code=201)
async def create_employee(data: schemas.EmployeeCreate, db: AsyncSession = Depends(get_db)):
    emp = await crud.create_employee(db, data)
    return schemas.EmployeeRead(**employee_to_read_dict(emp, reveal_sensitive=False))


@router.patch("/{employee_id}", response_model=schemas.EmployeeRead)
async def update_employee(
    employee_id: int,
    data: schemas.EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    emp = await crud.update_employee(db, emp, data)
    return schemas.EmployeeRead(**employee_to_read_dict(emp, reveal_sensitive=False))


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    await crud.delete_employee(db, emp)


# ---------- 眷屬 ----------
@router.get("/{employee_id}/dependents", response_model=List[schemas.DependentRead])
async def list_dependents(
    employee_id: int,
    reveal_sensitive: bool = Query(False, description="是否回傳眷屬身分證明文"),
    db: AsyncSession = Depends(get_db),
):
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    deps = await crud.list_dependents_by_employee(db, employee_id)
    reveal = _reveal(reveal_sensitive)
    return [schemas.DependentRead(**dependent_to_read_dict(d, reveal)) for d in deps]


@router.post("/{employee_id}/dependents", response_model=schemas.DependentRead, status_code=201)
async def create_dependent(
    employee_id: int,
    data: schemas.DependentCreate,
    db: AsyncSession = Depends(get_db),
):
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    dep = await crud.create_dependent(db, employee_id, data)
    return schemas.DependentRead(**dependent_to_read_dict(dep, reveal_sensitive=False))


@router.patch("/{employee_id}/dependents/{dependent_id}", response_model=schemas.DependentRead)
async def update_dependent(
    employee_id: int,
    dependent_id: int,
    data: schemas.DependentUpdate,
    db: AsyncSession = Depends(get_db),
):
    dep = await crud.get_dependent(db, dependent_id)
    if not dep or dep.employee_id != employee_id:
        raise HTTPException(status_code=404, detail="眷屬不存在")
    dep = await crud.update_dependent(db, dep, data)
    return schemas.DependentRead(**dependent_to_read_dict(dep, reveal_sensitive=False))


@router.delete("/{employee_id}/dependents/{dependent_id}", status_code=204)
async def delete_dependent(
    employee_id: int,
    dependent_id: int,
    db: AsyncSession = Depends(get_db),
):
    dep = await crud.get_dependent(db, dependent_id)
    if not dep or dep.employee_id != employee_id:
        raise HTTPException(status_code=404, detail="眷屬不存在")
    await crud.delete_dependent(db, dep)


# ---------- 薪資設定 salary_profile（第二階段排班/會計用） ----------
@router.get("/{employee_id}/salary-profile", response_model=Optional[schemas.SalaryProfileRead])
async def get_employee_salary_profile(employee_id: int, db: AsyncSession = Depends(get_db)):
    emp = await crud.get_employee(db, employee_id, load_dependents=False)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    profile = await crud.get_salary_profile(db, employee_id)
    return schemas.SalaryProfileRead.model_validate(profile) if profile else None


@router.put("/{employee_id}/salary-profile", response_model=schemas.SalaryProfileRead)
async def upsert_employee_salary_profile(
    employee_id: int,
    body: schemas.SalaryProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    emp = await crud.get_employee(db, employee_id, load_dependents=False)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    profile = await crud.upsert_salary_profile(
        db,
        employee_id=employee_id,
        salary_type=body.salary_type,
        monthly_base=Decimal(str(body.monthly_base)) if body.monthly_base is not None else None,
        daily_rate=Decimal(str(body.daily_rate)) if body.daily_rate is not None else None,
        hourly_rate=Decimal(str(body.hourly_rate)) if body.hourly_rate is not None else None,
        overtime_eligible=body.overtime_eligible,
        calculation_rules=body.calculation_rules,
    )
    await db.commit()
    await db.refresh(profile)
    return schemas.SalaryProfileRead.model_validate(profile)
