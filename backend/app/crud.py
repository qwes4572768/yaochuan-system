"""CRUD 操作 - 員工、眷屬、檔案；寫入時敏感欄位加密"""
from datetime import date
from decimal import Decimal
from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Employee, Dependent, EmployeeDocument, InsuranceConfig, RateTable, RateItem,
    InsuranceBracketImport, InsuranceBracket,
    SalaryProfile, InsuranceMonthlyResult, Site, SiteEmployeeAssignment,
    SiteContractFile, SiteRebate, SiteMonthlyReceipt,
    Schedule, ScheduleShift, ScheduleAssignment, SHIFT_CODES, ASSIGNMENT_ROLES, SCHEDULE_STATUSES,
    AccountingPayrollResult,
)
from app.schemas import (
    EmployeeCreate, EmployeeUpdate, DependentCreate, DependentUpdate,
    SiteCreate, SiteUpdate, SiteAssignmentCreate, SiteAssignmentUpdate,
    SiteRebateCreate, SiteRebateUpdate, SiteMonthlyReceiptCreate, SiteMonthlyReceiptUpdate,
    ScheduleCreate, ScheduleUpdate, ScheduleShiftCreate, ScheduleShiftUpdate, ScheduleShiftBatchCreate,
    ScheduleAssignmentCreate, ScheduleAssignmentUpdate,
)
from app.crypto import encrypt


async def get_employee(db: AsyncSession, employee_id: int, load_dependents: bool = True) -> Optional[Employee]:
    q = select(Employee).where(Employee.id == employee_id)
    if load_dependents:
        q = q.options(selectinload(Employee.dependents))
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def get_employee_by_name(
    db: AsyncSession, name: str, load_salary_profile: bool = False
) -> Optional[Employee]:
    """依姓名查詢員工（精確比對）；多人同名時回傳第一筆。供會計保全薪資等使用。"""
    if not name or not str(name).strip():
        return None
    q = select(Employee).where(Employee.name == name.strip()).limit(1)
    if load_salary_profile:
        q = q.options(selectinload(Employee.salary_profile))
    r = await db.execute(q)
    return r.scalars().first()


async def get_employee_by_name_with_registration_priority(
    db: AsyncSession,
    name: str,
    current_registration_type: str,
    extra_registration_types: Optional[List[str]] = None,
    load_salary_profile: bool = False,
) -> Optional[Employee]:
    """
    依固定優先序查詢員工：
    1) current_registration_type
    2) extra_registration_types（依傳入順序）
    """
    if not name or not str(name).strip():
        return None
    target_name = name.strip()
    seen: set[str] = set()
    ordered_types: List[str] = []
    for t in [current_registration_type, *(extra_registration_types or [])]:
        key = (t or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered_types.append(key)

    for registration_type in ordered_types:
        q = (
            select(Employee)
            .where(
                Employee.name == target_name,
                Employee.registration_type == registration_type,
            )
            .limit(1)
        )
        if load_salary_profile:
            q = q.options(selectinload(Employee.salary_profile))
        r = await db.execute(q)
        emp = r.scalars().first()
        if emp:
            return emp
    return None


async def list_employees(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    load_dependents: bool = False,
    search: Optional[str] = None,
    registration_type: Optional[str] = None,
) -> List[Employee]:
    q = select(Employee).order_by(Employee.id)
    if load_dependents:
        q = q.options(selectinload(Employee.dependents))
    if search and search.strip():
        s = f"%{search.strip()}%"
        q = q.where(Employee.name.ilike(s))
    if registration_type and registration_type.strip() in ("security", "property", "smith", "lixiang"):
        q = q.where(Employee.registration_type == registration_type.strip())
    q = q.offset(skip).limit(limit)
    r = await db.execute(q)
    return list(r.scalars().all())


def _encrypt_employee_fields(data: dict) -> dict:
    out = dict(data)
    if out.get("national_id"):
        out["national_id"] = encrypt(out["national_id"])
    if out.get("reg_address"):
        out["reg_address"] = encrypt(out["reg_address"])
    if out.get("live_address"):
        out["live_address"] = encrypt(out["live_address"])
    return out


def _encrypt_dependent_national_id(v: Optional[str]) -> Optional[str]:
    return encrypt(v) if v else None


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    raw = data.model_dump()
    enc = _encrypt_employee_fields(raw)
    emp = Employee(
        name=enc["name"],
        birth_date=enc["birth_date"],
        national_id=enc["national_id"],
        reg_address=enc["reg_address"],
        live_address=enc["live_address"],
        live_same_as_reg=enc.get("live_same_as_reg", False),
        salary_type=enc.get("salary_type"),
        salary_value=enc.get("salary_value"),
        insured_salary_level=enc.get("insured_salary_level"),
        enroll_date=enc.get("enroll_date"),
        cancel_date=enc.get("cancel_date"),
        dependent_count=enc.get("dependent_count", 0),
        pension_self_6=enc.get("pension_self_6", False),
        registration_type=enc.get("registration_type", "security"),
        notes=enc.get("notes"),
        pay_method=raw.get("pay_method") or "CASH",
        bank_code=raw.get("bank_code"),
        branch_code=raw.get("branch_code"),
        bank_account=raw.get("bank_account"),
        property_pay_mode=raw.get("property_pay_mode"),
        security_pay_mode=raw.get("security_pay_mode"),
        smith_pay_mode=raw.get("smith_pay_mode"),
        lixiang_pay_mode=raw.get("lixiang_pay_mode"),
        weekly_amount=raw.get("weekly_amount"),
        property_salary=raw.get("property_salary"),
    )
    db.add(emp)
    await db.flush()
    if data.dependents:
        for d in data.dependents:
            dep = Dependent(
                employee_id=emp.id,
                name=d.name,
                birth_date=d.birth_date,
                national_id=_encrypt_dependent_national_id(d.national_id),
                relation=d.relation,
                city=d.city,
                is_disabled=d.is_disabled,
                disability_level=d.disability_level if d.is_disabled else None,
                notes=d.notes,
            )
            db.add(dep)
    await db.refresh(emp)
    await db.refresh(emp, attribute_names=["dependents"])
    return emp


async def update_employee(db: AsyncSession, emp: Employee, data: EmployeeUpdate) -> Employee:
    update_data = data.model_dump(exclude_unset=True)
    if "national_id" in update_data and update_data["national_id"] is not None:
        update_data["national_id"] = encrypt(update_data["national_id"])
    if "reg_address" in update_data and update_data["reg_address"] is not None:
        update_data["reg_address"] = encrypt(update_data["reg_address"])
    if "live_address" in update_data and update_data["live_address"] is not None:
        update_data["live_address"] = encrypt(update_data["live_address"])
    for k, v in update_data.items():
        setattr(emp, k, v)
    await db.flush()
    await db.refresh(emp)
    await db.refresh(emp, attribute_names=["dependents"])
    return emp


async def delete_employee(db: AsyncSession, emp: Employee) -> None:
    await db.delete(emp)


async def delete_all_employees(db: AsyncSession) -> int:
    """刪除所有員工（災難復原還原前用）；cascade 會刪除眷屬等。回傳刪除筆數。"""
    r = await db.execute(select(Employee))
    rows = list(r.scalars().all())
    for emp in rows:
        await db.delete(emp)
    return len(rows)


# ---------- 眷屬 ----------
async def get_dependent(db: AsyncSession, dependent_id: int) -> Optional[Dependent]:
    r = await db.execute(select(Dependent).where(Dependent.id == dependent_id))
    return r.scalar_one_or_none()


async def list_dependents_by_employee(db: AsyncSession, employee_id: int) -> List[Dependent]:
    r = await db.execute(
        select(Dependent).where(Dependent.employee_id == employee_id).order_by(Dependent.id)
    )
    return list(r.scalars().all())


async def create_dependent(db: AsyncSession, employee_id: int, data: DependentCreate) -> Dependent:
    dep = Dependent(
        employee_id=employee_id,
        name=data.name,
        birth_date=data.birth_date,
        national_id=_encrypt_dependent_national_id(data.national_id),
        relation=data.relation,
        city=data.city,
        is_disabled=data.is_disabled,
        disability_level=data.disability_level if data.is_disabled else None,
        notes=data.notes,
    )
    db.add(dep)
    await db.flush()
    await db.refresh(dep)
    return dep


async def update_dependent(db: AsyncSession, dep: Dependent, data: DependentUpdate) -> Dependent:
    update_data = data.model_dump(exclude_unset=True)
    if "national_id" in update_data and update_data["national_id"] is not None:
        update_data["national_id"] = encrypt(update_data["national_id"])
    if update_data.get("is_disabled") is False:
        update_data["disability_level"] = None
    for k, v in update_data.items():
        setattr(dep, k, v)
    await db.flush()
    await db.refresh(dep)
    return dep


async def delete_dependent(db: AsyncSession, dep: Dependent) -> None:
    await db.delete(dep)


# ---------- 檔案（上傳後可更新 employee.safety_pdf_path / contract_84_1_pdf_path） ----------
async def add_document(
    db: AsyncSession,
    employee_id: int,
    document_type: str,
    file_name: str,
    file_path: str,
    file_size: Optional[int] = None,
) -> EmployeeDocument:
    doc = EmployeeDocument(
        employee_id=employee_id,
        document_type=document_type,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
    )
    db.add(doc)
    await db.flush()
    emp = await get_employee(db, employee_id, load_dependents=False)
    if emp:
        if document_type == "safety_check":
            emp.safety_pdf_path = file_path
        elif document_type == "84_1":
            emp.contract_84_1_pdf_path = file_path
        await db.flush()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, doc_id: int) -> Optional[EmployeeDocument]:
    r = await db.execute(select(EmployeeDocument).where(EmployeeDocument.id == doc_id))
    return r.scalar_one_or_none()


async def list_documents_by_employee(db: AsyncSession, employee_id: int) -> List[EmployeeDocument]:
    r = await db.execute(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id)
    )
    return list(r.scalars().all())


# ---------- 費率設定表 (insurance_config) ----------
INSURANCE_KEYS = ("labor_insurance", "health_insurance", "occupational_accident", "labor_pension", "group_insurance")


async def get_insurance_config(db: AsyncSession, config_key: str) -> Optional[str]:
    r = await db.execute(select(InsuranceConfig).where(InsuranceConfig.config_key == config_key))
    row = r.scalar_one_or_none()
    return row.config_value if row else None


async def set_insurance_config(db: AsyncSession, config_key: str, config_value: str, description: Optional[str] = None) -> InsuranceConfig:
    from datetime import datetime
    r = await db.execute(select(InsuranceConfig).where(InsuranceConfig.config_key == config_key))
    row = r.scalar_one_or_none()
    if row:
        row.config_value = config_value
        row.updated_at = datetime.utcnow()
        if description is not None:
            row.description = description
        await db.flush()
        await db.refresh(row)
        return row
    row = InsuranceConfig(config_key=config_key, config_value=config_value, description=description)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_all_insurance_rules(db: AsyncSession, year: Optional[int] = None, month: Optional[int] = None) -> dict:
    """
    取得費率/級距。若提供 year, month，優先依「計算月份」從 rate_tables 取當月有效版本；
    缺的類型或無有效表時，以設定表(insurance_config)或 YAML 補齊。
    """
    import json
    from app.services.insurance_calc import _load_rules_from_yaml
    fallback = _load_rules_from_yaml()
    result = dict(fallback)
    # 先從設定表補齊（舊方式）
    for key in INSURANCE_KEYS:
        val = await get_insurance_config(db, key)
        if val:
            try:
                result[key] = json.loads(val)
            except Exception:
                pass
    # 若有指定計算月份，以 rate_tables 當月有效版本覆蓋
    if year is not None and month is not None:
        as_of = date(year, month, 1)
        rules_from_tables = await build_rules_from_rate_tables(db, as_of)
        if rules_from_tables:
            for k, v in rules_from_tables.items():
                if v is not None:
                    result[k] = v
    return result


async def build_rules_from_rate_tables(db: AsyncSession, as_of: date) -> Dict[str, Any]:
    """
    依 as_of 日期取得各類型有效級距表，組成試算用 rules 結構。
    回傳 { labor_insurance?, health_insurance?, occupational_accident?, labor_pension? }，缺的為 None。
    """
    out: Dict[str, Any] = {}
    for t in RATE_TABLE_TYPES:
        tbl = await get_effective_rate_table(db, t, as_of)
        if not tbl:
            out[t] = None
            continue
        items = sorted(tbl.items, key=lambda x: (x.salary_min, x.salary_max))
        if t == "labor_insurance":
            # brackets: [ (low, high, level), ... ]；rate / employer_ratio / employee_ratio / government_ratio
            first = items[0] if items else None
            out[t] = {
                "rate": float(tbl.total_rate) if tbl.total_rate is not None else 0.115,
                "employer_ratio": float(first.employer_rate) if first else 0.7,
                "employee_ratio": float(first.employee_rate) if first else 0.2,
                "government_ratio": float(first.gov_rate) if first and first.gov_rate is not None else 0.1,
                "brackets": [
                    [int(it.salary_min), int(it.salary_max), int(it.insured_salary or it.salary_max)]
                    for it in items
                ],
            }
        elif t == "health_insurance":
            first = items[0] if items else None
            out[t] = {
                "rate": float(tbl.total_rate) if tbl.total_rate is not None else 0.0517,
                "employer_ratio": float(first.employer_rate) if first else 0.6,
                "employee_ratio": float(first.employee_rate) if first else 0.3,
                "max_dependents_count": 3,
            }
        elif t == "occupational_accident":
            first = items[0] if items else None
            out[t] = {
                "rate": float(tbl.total_rate) if tbl.total_rate is not None else 0.0022,
                "employer_ratio": float(first.employer_rate) if first else 1,
            }
        elif t == "labor_pension":
            first = items[0] if items else None
            out[t] = {
                "employer_ratio": float(first.employer_rate) if first else 0.06,
            }
        else:
            out[t] = None
    return out


# ---------- rate_tables / rate_items ----------
RATE_TABLE_TYPES = ("labor_insurance", "health_insurance", "occupational_accident", "labor_pension")


async def get_effective_rate_table(db: AsyncSession, table_type: str, as_of: date) -> Optional[RateTable]:
    """取得某類型在 as_of 當日有效的級距表（effective_from <= as_of <= effective_to）"""
    q = (
        select(RateTable)
        .where(RateTable.type == table_type)
        .where(RateTable.effective_from <= as_of)
        .where((RateTable.effective_to.is_(None)) | (RateTable.effective_to >= as_of))
        .order_by(RateTable.effective_from.desc())
    )
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def list_rate_tables(db: AsyncSession, table_type: Optional[str] = None) -> List[RateTable]:
    """列出級距表，可篩選 type；含 items"""
    q = select(RateTable).order_by(RateTable.type, RateTable.effective_from.desc())
    if table_type:
        q = q.where(RateTable.type == table_type)
    q = q.options(selectinload(RateTable.items))
    r = await db.execute(q)
    return list(r.scalars().all())


async def get_rate_table_by_id(db: AsyncSession, table_id: int) -> Optional[RateTable]:
    """依 id 取得級距表（含 items）"""
    r = await db.execute(
        select(RateTable).where(RateTable.id == table_id).options(selectinload(RateTable.items))
    )
    return r.scalar_one_or_none()


# ---------- insurance_bracket_imports / insurance_brackets（權威級距表：查表計費）----------
async def get_latest_bracket_import(db: AsyncSession) -> Optional[InsuranceBracketImport]:
    """取得最近一筆級距表匯入（含 brackets）"""
    r = await db.execute(
        select(InsuranceBracketImport)
        .order_by(InsuranceBracketImport.imported_at.desc())
        .limit(1)
        .options(selectinload(InsuranceBracketImport.brackets))
    )
    return r.scalar_one_or_none()


async def get_bracket_by_level(
    db: AsyncSession, import_id: int, insured_salary_level: int
) -> Optional[InsuranceBracket]:
    """在指定匯入的級距表中，依投保級距（整數）查詢一筆"""
    r = await db.execute(
        select(InsuranceBracket).where(
            InsuranceBracket.import_id == import_id,
            InsuranceBracket.insured_salary_level == insured_salary_level,
        )
    )
    return r.scalar_one_or_none()


async def create_bracket_import(
    db: AsyncSession,
    file_name: str,
    file_path: Optional[str],
    row_count: int,
    version: Optional[str] = None,
    brackets: Optional[List[Dict[str, Any]]] = None,
) -> InsuranceBracketImport:
    """新增一筆級距表匯入與其明細；brackets 為 [{"insured_salary_level": int, "labor_employer": Decimal, ...}, ...]"""
    imp = InsuranceBracketImport(
        file_name=file_name,
        file_path=file_path,
        row_count=row_count,
        version=version,
    )
    db.add(imp)
    await db.flush()
    if brackets:
        for row in brackets:
            b = InsuranceBracket(
                import_id=imp.id,
                insured_salary_level=int(row["insured_salary_level"]),
                labor_employer=Decimal(str(row.get("labor_employer", 0))),
                labor_employee=Decimal(str(row.get("labor_employee", 0))),
                health_employer=Decimal(str(row.get("health_employer", 0))),
                health_employee=Decimal(str(row.get("health_employee", 0))),
                occupational_accident=Decimal(str(row.get("occupational_accident", 0))),
                labor_pension=Decimal(str(row.get("labor_pension", 0))),
                group_insurance=Decimal(str(row.get("group_insurance", 0))),
            )
            db.add(b)
    await db.flush()
    await db.refresh(imp)
    return imp


# ---------- salary_profile ----------
async def get_salary_profile(db: AsyncSession, employee_id: int) -> Optional[SalaryProfile]:
    r = await db.execute(select(SalaryProfile).where(SalaryProfile.employee_id == employee_id))
    return r.scalar_one_or_none()


async def upsert_salary_profile(
    db: AsyncSession,
    employee_id: int,
    salary_type: str,
    monthly_base: Optional[Decimal] = None,
    daily_rate: Optional[Decimal] = None,
    hourly_rate: Optional[Decimal] = None,
    overtime_eligible: bool = False,
    calculation_rules: Optional[str] = None,
) -> SalaryProfile:
    from datetime import datetime
    row = await get_salary_profile(db, employee_id)
    if row:
        row.salary_type = salary_type
        row.monthly_base = monthly_base
        row.daily_rate = daily_rate
        row.hourly_rate = hourly_rate
        row.overtime_eligible = overtime_eligible
        row.calculation_rules = calculation_rules
        row.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(row)
        return row
    row = SalaryProfile(
        employee_id=employee_id,
        salary_type=salary_type,
        monthly_base=monthly_base,
        daily_rate=daily_rate,
        hourly_rate=hourly_rate,
        overtime_eligible=overtime_eligible,
        calculation_rules=calculation_rules,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


# ---------- insurance_monthly_result ----------
INSURANCE_ITEM_TYPES = ("labor_insurance", "health_insurance", "occupational_accident", "labor_pension", "group_insurance")


async def list_insurance_monthly_results(
    db: AsyncSession,
    year_month: int,
    employee_id: Optional[int] = None,
) -> List[InsuranceMonthlyResult]:
    q = select(InsuranceMonthlyResult).where(InsuranceMonthlyResult.year_month == year_month)
    if employee_id is not None:
        q = q.where(InsuranceMonthlyResult.employee_id == employee_id)
    q = q.order_by(InsuranceMonthlyResult.employee_id, InsuranceMonthlyResult.item_type)
    r = await db.execute(q)
    return list(r.scalars().all())


async def upsert_insurance_monthly_result(
    db: AsyncSession,
    employee_id: int,
    year_month: int,
    item_type: str,
    employee_amount: Decimal,
    employer_amount: Decimal,
    gov_amount: Optional[Decimal] = None,
) -> InsuranceMonthlyResult:
    from sqlalchemy import and_
    r = await db.execute(
        select(InsuranceMonthlyResult).where(
            and_(
                InsuranceMonthlyResult.employee_id == employee_id,
                InsuranceMonthlyResult.year_month == year_month,
                InsuranceMonthlyResult.item_type == item_type,
            )
        )
    )
    row = r.scalar_one_or_none()
    if row:
        row.employee_amount = employee_amount
        row.employer_amount = employer_amount
        row.gov_amount = gov_amount
        await db.flush()
        await db.refresh(row)
        return row
    row = InsuranceMonthlyResult(
        employee_id=employee_id,
        year_month=year_month,
        item_type=item_type,
        employee_amount=employee_amount,
        employer_amount=employer_amount,
        gov_amount=gov_amount,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def delete_insurance_monthly_results_for_month(db: AsyncSession, year_month: int) -> int:
    """刪除某年月的保險結果（重新產生前可先清空）"""
    from sqlalchemy import delete
    r = await db.execute(delete(InsuranceMonthlyResult).where(InsuranceMonthlyResult.year_month == year_month))
    return r.rowcount


# ---------- 案場 sites ----------
async def get_site(db: AsyncSession, site_id: int, load_assignments: bool = False) -> Optional[Site]:
    q = select(Site).where(Site.id == site_id)
    if load_assignments:
        q = q.options(selectinload(Site.assignments).selectinload(SiteEmployeeAssignment.employee))
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def get_site_by_name(db: AsyncSession, name: str) -> Optional[Site]:
    """依案場名稱查詢（精確比對）；供會計保全薪資等使用。"""
    if not name or not str(name).strip():
        return None
    r = await db.execute(select(Site).where(Site.name == name.strip()).limit(1))
    return r.scalars().first()


ARCHIVED_REASON_EXPIRED_NO_RENEW = "expired_no_renew"


async def run_expired_archive_check(db: AsyncSession) -> None:
    """到期未續約歸檔：contract_end < today 且 is_active 仍為 True 的案場，設為歷史案場並自現行列表隱藏。"""
    if not hasattr(Site, "is_archived"):
        return
    from datetime import datetime
    today = date.today()
    stmt = select(Site).where(
        Site.contract_end.is_not(None),
        Site.contract_end < today,
        Site.is_active == True,
        Site.is_archived == False,  # noqa: E711
    )
    r = await db.execute(stmt)
    to_archive = list(r.scalars().all())
    for site in to_archive:
        site.is_archived = True
        site.archived_at = datetime.utcnow()
        site.archived_reason = ARCHIVED_REASON_EXPIRED_NO_RENEW
        site.is_active = False
    if to_archive:
        await db.flush()


# [完成] list_sites 分頁/total/items/q/contract_active 已驗證；擴充 site_type / service_types / status / include_inactive / is_archived
async def list_sites(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    load_assignments: bool = False,
    q: Optional[str] = None,
    payment_method: Optional[str] = None,
    is_84_1: Optional[bool] = None,
    contract_active: Optional[bool] = None,
    site_type: Optional[str] = None,
    service_types: Optional[str] = None,
    status: Optional[str] = None,
    include_inactive: bool = False,
) -> Tuple[List[Site], int]:
    """案場列表（現行）：只含 is_archived=False。預設 is_active=True；include_inactive 時含手動移除（is_active=False）。"""
    # 1) base_stmt：現行列表不含歷史案場
    base_stmt = select(Site)
    if getattr(Site, "is_archived", None) is not None:
        base_stmt = base_stmt.where(Site.is_archived == False)  # noqa: E711
    if not include_inactive:
        base_stmt = base_stmt.where(Site.is_active == True)

    if q and q.strip():
        kw = f"%{q.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                Site.name.ilike(kw),
                Site.client_name.ilike(kw),
                Site.address.ilike(kw),
                Site.customer_name.ilike(kw),
            )
        )

    if payment_method and payment_method.strip():
        base_stmt = base_stmt.where(Site.payment_method == payment_method.strip())

    if is_84_1 is not None:
        base_stmt = base_stmt.where(Site.is_84_1 == is_84_1)

    if contract_active is not None:
        today = date.today()
        if contract_active:
            base_stmt = base_stmt.where(or_(Site.contract_end.is_(None), Site.contract_end >= today))
        else:
            base_stmt = base_stmt.where(Site.contract_end.is_not(None), Site.contract_end < today)

    if site_type and site_type.strip():
        base_stmt = base_stmt.where(Site.site_type == site_type.strip())

    if service_types and service_types.strip():
        # service_types 為 JSON 陣列字串，例如 ["駐衛保全服務"]；單一類型也可傳 "駐衛保全服務"
        base_stmt = base_stmt.where(Site.service_types.is_not(None), Site.service_types.contains(service_types.strip()))

    if status and status.strip():
        from datetime import timedelta
        today = date.today()
        threshold = today + timedelta(days=30)  # 即將到期：30 天內
        if status.strip() == "expired":
            base_stmt = base_stmt.where(Site.contract_end.is_not(None), Site.contract_end < today)
        elif status.strip() == "expiring":
            base_stmt = base_stmt.where(
                Site.contract_end.is_not(None),
                Site.contract_end >= today,
                Site.contract_end <= threshold,
            )
        elif status.strip() == "normal":
            base_stmt = base_stmt.where(
                or_(Site.contract_end.is_(None), Site.contract_end > threshold),
            )

    # 2) total：select(func.count()).select_from(base_stmt.subquery())
    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(total_stmt)
    total = int(total or 0)

    # 3) items：在 base_stmt 上加 order_by、offset、limit，保留 selectinload
    offset = (page - 1) * page_size
    items_stmt = base_stmt.order_by(Site.id.desc()).offset(offset).limit(page_size)
    if load_assignments:
        items_stmt = items_stmt.options(selectinload(Site.assignments).selectinload(SiteEmployeeAssignment.employee))
    r = await db.execute(items_stmt)
    items = list(r.scalars().all())

    return items, total


async def list_sites_history(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Site], int]:
    """歷史案場列表：is_archived=True 且 archived_reason=expired_no_renew（排除手動移除）。支援分頁、q、status。"""
    if not hasattr(Site, "is_archived"):
        return [], 0
    base_stmt = select(Site).where(
        Site.is_archived == True,  # noqa: E711
        Site.archived_reason == ARCHIVED_REASON_EXPIRED_NO_RENEW,
    )
    if q and q.strip():
        kw = f"%{q.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                Site.name.ilike(kw),
                Site.client_name.ilike(kw),
                Site.address.ilike(kw),
                Site.customer_name.ilike(kw),
            )
        )
    if status and status.strip():
        today = date.today()
        from datetime import timedelta
        threshold = today + timedelta(days=30)
        if status.strip() == "expired":
            base_stmt = base_stmt.where(Site.contract_end.is_not(None), Site.contract_end < today)
        elif status.strip() == "expiring":
            base_stmt = base_stmt.where(
                Site.contract_end.is_not(None),
                Site.contract_end >= today,
                Site.contract_end <= threshold,
            )
        elif status.strip() == "normal":
            base_stmt = base_stmt.where(
                or_(Site.contract_end.is_(None), Site.contract_end > threshold),
            )
    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(total_stmt)
    total = int(total or 0)
    offset = (page - 1) * page_size
    items_stmt = base_stmt.order_by(Site.id.desc()).offset(offset).limit(page_size)
    r = await db.execute(items_stmt)
    items = list(r.scalars().all())
    return items, total


async def create_site(db: AsyncSession, data: SiteCreate) -> Site:
    raw = data.model_dump(exclude_unset=True)
    # 既有必填欄位：若未送或為空則由案場管理欄位推導
    if not raw.get("client_name"):
        raw["client_name"] = (data.customer_name or data.name or "").strip() or data.name
    if raw.get("monthly_amount") is None:
        raw["monthly_amount"] = data.monthly_fee_incl_tax or data.monthly_amount or Decimal("0")
    if not raw.get("payment_method"):
        raw["payment_method"] = data.payment_method or "transfer"
    if raw.get("receivable_day") is None:
        raw["receivable_day"] = data.receivable_day or data.payment_due_day or 1
    site = Site(**raw)
    db.add(site)
    await db.flush()
    await db.refresh(site)
    return site


class SiteInactiveError(ValueError):
    """案場已移除，不可編輯"""
    pass


async def update_site(db: AsyncSession, site: Site, data: SiteUpdate) -> Site:
    if not getattr(site, "is_active", True):
        raise SiteInactiveError("已移除的案場不可編輯")
    if getattr(site, "is_archived", False):
        raise SiteInactiveError("歷史案場不可編輯")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(site, k, v)
    await db.flush()
    await db.refresh(site)
    return site


async def delete_site(db: AsyncSession, site: Site) -> None:
    await db.delete(site)


async def deactivate_site(db: AsyncSession, site: Site, reason: str = "manual") -> Site:
    """軟刪除：設定 is_active=False, deactivated_at=now(), deactivated_reason。不實體刪除。"""
    from datetime import datetime
    site.is_active = False
    site.deactivated_at = datetime.utcnow()
    site.deactivated_reason = reason
    await db.flush()
    await db.refresh(site)
    return site


async def get_monthly_receipts_for_sites(
    db: AsyncSession, site_ids: List[int], billing_month: str
) -> List[SiteMonthlyReceipt]:
    """取得多個案場在指定年月的入帳紀錄（用於列表顯示本月是否入帳、應收金額）。"""
    if not site_ids:
        return []
    r = await db.execute(
        select(SiteMonthlyReceipt).where(
            SiteMonthlyReceipt.site_id.in_(site_ids),
            SiteMonthlyReceipt.billing_month == billing_month,
        )
    )
    return list(r.scalars().all())


# ---------- 案場回饋 site_rebates ----------
async def list_rebates_by_site(db: AsyncSession, site_id: int) -> List[SiteRebate]:
    r = await db.execute(select(SiteRebate).where(SiteRebate.site_id == site_id).order_by(SiteRebate.id.desc()))
    return list(r.scalars().all())


async def get_rebate(db: AsyncSession, rebate_id: int) -> Optional[SiteRebate]:
    r = await db.execute(select(SiteRebate).where(SiteRebate.id == rebate_id))
    return r.scalar_one_or_none()


async def create_rebate(db: AsyncSession, site_id: int, data: SiteRebateCreate) -> SiteRebate:
    rebate = SiteRebate(site_id=site_id, **data.model_dump())
    db.add(rebate)
    await db.flush()
    await db.refresh(rebate)
    return rebate


async def update_rebate(db: AsyncSession, rebate: SiteRebate, data: SiteRebateUpdate) -> SiteRebate:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rebate, k, v)
    await db.flush()
    await db.refresh(rebate)
    return rebate


async def delete_rebate(db: AsyncSession, rebate: SiteRebate) -> None:
    await db.delete(rebate)


async def set_rebate_receipt_path(db: AsyncSession, rebate_id: int, file_path: str) -> Optional[SiteRebate]:
    rebate = await get_rebate(db, rebate_id)
    if not rebate:
        return None
    rebate.receipt_pdf_path = file_path
    await db.flush()
    await db.refresh(rebate)
    return rebate


# ---------- 案場每月入帳 site_monthly_receipts ----------
async def list_monthly_receipts_by_site(
    db: AsyncSession, site_id: int, year: Optional[int] = None
) -> List[SiteMonthlyReceipt]:
    q = select(SiteMonthlyReceipt).where(SiteMonthlyReceipt.site_id == site_id)
    if year is not None:
        q = q.where(SiteMonthlyReceipt.billing_month >= f"{year}-01", SiteMonthlyReceipt.billing_month <= f"{year}-12")
    q = q.order_by(SiteMonthlyReceipt.billing_month.desc())
    r = await db.execute(q)
    return list(r.scalars().all())


async def get_monthly_receipt(db: AsyncSession, receipt_id: int) -> Optional[SiteMonthlyReceipt]:
    r = await db.execute(select(SiteMonthlyReceipt).where(SiteMonthlyReceipt.id == receipt_id))
    return r.scalar_one_or_none()


async def create_monthly_receipt(
    db: AsyncSession, site_id: int, data: SiteMonthlyReceiptCreate, default_expected: Optional[Decimal] = None
) -> SiteMonthlyReceipt:
    raw = data.model_dump()
    if raw.get("expected_amount") is None and default_expected is not None:
        raw["expected_amount"] = default_expected
    rec = SiteMonthlyReceipt(site_id=site_id, **raw)
    db.add(rec)
    await db.flush()
    await db.refresh(rec)
    return rec


async def create_monthly_receipts_for_year(
    db: AsyncSession, site_id: int, year: int, default_expected: Optional[Decimal] = None
) -> List[SiteMonthlyReceipt]:
    """建立指定年度 1～12 月的入帳紀錄（若該月已存在則略過）。"""
    existing = await list_monthly_receipts_by_site(db, site_id, year=year)
    existing_months = {r.billing_month for r in existing}
    created = []
    for month in range(1, 13):
        billing_month = f"{year}-{month:02d}"
        if billing_month in existing_months:
            continue
        rec = SiteMonthlyReceipt(
            site_id=site_id,
            billing_month=billing_month,
            expected_amount=default_expected,
            is_received=False,
        )
        db.add(rec)
        await db.flush()
        await db.refresh(rec)
        created.append(rec)
    return created


async def update_monthly_receipt(db: AsyncSession, rec: SiteMonthlyReceipt, data: SiteMonthlyReceiptUpdate) -> SiteMonthlyReceipt:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rec, k, v)
    await db.flush()
    await db.refresh(rec)
    return rec


async def set_monthly_receipt_proof_path(db: AsyncSession, receipt_id: int, file_path: str) -> Optional[SiteMonthlyReceipt]:
    rec = await get_monthly_receipt(db, receipt_id)
    if not rec:
        return None
    rec.proof_pdf_path = file_path
    await db.flush()
    await db.refresh(rec)
    return rec


# ---------- 案場-員工指派 site_employee_assignments ----------
async def get_assignment(db: AsyncSession, assignment_id: int) -> Optional[SiteEmployeeAssignment]:
    r = await db.execute(
        select(SiteEmployeeAssignment)
        .where(SiteEmployeeAssignment.id == assignment_id)
        .options(
            selectinload(SiteEmployeeAssignment.site),
            selectinload(SiteEmployeeAssignment.employee),
        )
    )
    return r.scalar_one_or_none()


async def list_assignments_by_site(
    db: AsyncSession,
    site_id: int,
    load_employee: bool = True,
) -> List[SiteEmployeeAssignment]:
    q = select(SiteEmployeeAssignment).where(SiteEmployeeAssignment.site_id == site_id).order_by(SiteEmployeeAssignment.id)
    if load_employee:
        q = q.options(selectinload(SiteEmployeeAssignment.employee))
    r = await db.execute(q)
    return list(r.scalars().all())


async def list_assignments_by_employee(
    db: AsyncSession,
    employee_id: int,
    load_site: bool = True,
) -> List[SiteEmployeeAssignment]:
    q = select(SiteEmployeeAssignment).where(SiteEmployeeAssignment.employee_id == employee_id).order_by(SiteEmployeeAssignment.id)
    if load_site:
        q = q.options(selectinload(SiteEmployeeAssignment.site))
    r = await db.execute(q)
    return list(r.scalars().all())


def _periods_overlap(
    a_from: Optional[date],
    a_to: Optional[date],
    b_from: Optional[date],
    b_to: Optional[date],
) -> bool:
    """兩段期間是否重疊。NULL 視為無界（from=最早、to=最晚）。"""
    from datetime import date as date_type
    INF_MIN = date_type(1, 1, 1)
    INF_MAX = date_type(9999, 12, 31)
    a1 = a_from if a_from is not None else INF_MIN
    a2 = a_to if a_to is not None else INF_MAX
    b1 = b_from if b_from is not None else INF_MIN
    b2 = b_to if b_to is not None else INF_MAX
    return a1 <= b2 and b1 <= a2


async def check_assignment_period_overlap(
    db: AsyncSession,
    site_id: int,
    employee_id: int,
    effective_from: Optional[date],
    effective_to: Optional[date],
    exclude_assignment_id: Optional[int] = None,
) -> bool:
    """同一 site_id + employee_id 下，是否已有與給定期間重疊的指派。回傳 True 表示有重疊。"""
    q = select(SiteEmployeeAssignment).where(
        SiteEmployeeAssignment.site_id == site_id,
        SiteEmployeeAssignment.employee_id == employee_id,
    )
    if exclude_assignment_id is not None:
        q = q.where(SiteEmployeeAssignment.id != exclude_assignment_id)
    r = await db.execute(q)
    for existing in r.scalars().all():
        if _periods_overlap(
            effective_from, effective_to,
            existing.effective_from, existing.effective_to,
        ):
            return True
    return False


class AssignmentPeriodOverlapError(ValueError):
    """指派期間與既有指派重疊"""
    pass


async def create_assignment(
    db: AsyncSession,
    site_id: int,
    data: SiteAssignmentCreate,
) -> SiteEmployeeAssignment:
    overlap = await check_assignment_period_overlap(
        db, site_id, data.employee_id,
        data.effective_from, data.effective_to,
        exclude_assignment_id=None,
    )
    if overlap:
        raise AssignmentPeriodOverlapError("同一案場、同一員工之指派期間不可重疊")
    a = SiteEmployeeAssignment(
        site_id=site_id,
        employee_id=data.employee_id,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        notes=data.notes,
    )
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return a


async def update_assignment(db: AsyncSession, a: SiteEmployeeAssignment, data: SiteAssignmentUpdate) -> SiteEmployeeAssignment:
    update_data = data.model_dump(exclude_unset=True)
    new_from = update_data.get("effective_from", a.effective_from)
    new_to = update_data.get("effective_to", a.effective_to)
    overlap = await check_assignment_period_overlap(
        db, a.site_id, a.employee_id,
        new_from, new_to,
        exclude_assignment_id=a.id,
    )
    if overlap:
        raise AssignmentPeriodOverlapError("同一案場、同一員工之指派期間不可重疊")
    for k, v in update_data.items():
        setattr(a, k, v)
    await db.flush()
    await db.refresh(a)
    return a


async def delete_assignment(db: AsyncSession, a: SiteEmployeeAssignment) -> None:
    await db.delete(a)


# ---------- 排班 P0：schedules / schedule_shifts / schedule_assignments ----------
async def get_schedule(db: AsyncSession, schedule_id: int, load_shifts: bool = False) -> Optional[Schedule]:
    q = select(Schedule).where(Schedule.id == schedule_id)
    if load_shifts:
        q = q.options(selectinload(Schedule.shifts))
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def list_schedules(
    db: AsyncSession,
    site_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[Schedule]:
    q = select(Schedule).order_by(Schedule.site_id, Schedule.year.desc(), Schedule.month.desc())
    if site_id is not None:
        q = q.where(Schedule.site_id == site_id)
    if year is not None:
        q = q.where(Schedule.year == year)
    if month is not None:
        q = q.where(Schedule.month == month)
    r = await db.execute(q)
    return list(r.scalars().all())


async def create_schedule(db: AsyncSession, data: ScheduleCreate) -> Schedule:
    raw = data.model_dump()
    s = Schedule(**raw)
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


async def update_schedule(db: AsyncSession, s: Schedule, data: ScheduleUpdate) -> Schedule:
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(s, k, v)
    await db.flush()
    await db.refresh(s)
    return s


async def delete_schedule(db: AsyncSession, s: Schedule) -> None:
    await db.delete(s)


async def get_shift(db: AsyncSession, shift_id: int, load_assignments: bool = False) -> Optional[ScheduleShift]:
    q = select(ScheduleShift).where(ScheduleShift.id == shift_id)
    if load_assignments:
        q = q.options(selectinload(ScheduleShift.assignments).selectinload(ScheduleAssignment.employee))
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def list_shifts_by_schedule(
    db: AsyncSession,
    schedule_id: int,
    load_assignments: bool = False,
) -> List[ScheduleShift]:
    q = select(ScheduleShift).where(ScheduleShift.schedule_id == schedule_id).order_by(ScheduleShift.date, ScheduleShift.id)
    if load_assignments:
        q = q.options(selectinload(ScheduleShift.assignments).selectinload(ScheduleAssignment.employee))
    r = await db.execute(q)
    return list(r.scalars().all())


def _shift_duration_hours(start_time, end_time) -> Decimal:
    """依 start_time/end_time 計算工時（小時）；若缺則回傳 0。"""
    if not start_time or not end_time:
        return Decimal("0")
    from datetime import datetime, date
    d = date(2000, 1, 1)
    st = datetime.combine(d, start_time)
    et = datetime.combine(d, end_time)
    if et <= st:
        et = datetime.combine(date(2000, 1, 2), end_time)
    delta = et - st
    return Decimal(str(delta.total_seconds() / 3600))


async def create_shift(db: AsyncSession, schedule_id: int, data: ScheduleShiftCreate) -> ScheduleShift:
    raw = data.model_dump()
    sh = ScheduleShift(schedule_id=schedule_id, **raw)
    db.add(sh)
    await db.flush()
    await db.refresh(sh)
    return sh


async def batch_create_shifts_for_month(
    db: AsyncSession,
    schedule_id: int,
    year: int,
    month: int,
    template: ScheduleShiftBatchCreate,
) -> List[ScheduleShift]:
    """為該月每一天建立一筆 shift（依 template 的 shift_code、start_time、end_time、required_headcount）。"""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    created = []
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        sh = ScheduleShift(
            schedule_id=schedule_id,
            date=d,
            shift_code=template.shift_code,
            start_time=template.start_time,
            end_time=template.end_time,
            required_headcount=template.required_headcount,
        )
        db.add(sh)
        await db.flush()
        await db.refresh(sh)
        created.append(sh)
    return created


async def update_shift(db: AsyncSession, sh: ScheduleShift, data: ScheduleShiftUpdate) -> ScheduleShift:
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(sh, k, v)
    await db.flush()
    await db.refresh(sh)
    return sh


async def delete_shift(db: AsyncSession, sh: ScheduleShift) -> None:
    await db.delete(sh)


async def is_employee_eligible_for_site_on_date(
    db: AsyncSession,
    site_id: int,
    employee_id: int,
    on_date: date,
) -> bool:
    """該員工在 on_date 是否在該案場有效指派期間內（依 site_employee_assignments effective_from/to）。"""
    q = select(SiteEmployeeAssignment).where(
        SiteEmployeeAssignment.site_id == site_id,
        SiteEmployeeAssignment.employee_id == employee_id,
    )
    r = await db.execute(q)
    for a in r.scalars().all():
        eff_from = a.effective_from if a.effective_from is not None else date(1, 1, 1)
        eff_to = a.effective_to if a.effective_to is not None else date(9999, 12, 31)
        if eff_from <= on_date <= eff_to:
            return True
    return False


class ScheduleAssignmentNotEligibleError(ValueError):
    """員工在該班別日期不在案場有效指派期間內"""
    pass


async def get_schedule_assignment(db: AsyncSession, assignment_id: int) -> Optional[ScheduleAssignment]:
    r = await db.execute(
        select(ScheduleAssignment)
        .where(ScheduleAssignment.id == assignment_id)
        .options(
            selectinload(ScheduleAssignment.shift).selectinload(ScheduleShift.schedule),
            selectinload(ScheduleAssignment.employee),
        )
    )
    return r.scalar_one_or_none()


async def list_assignments_by_shift(db: AsyncSession, shift_id: int, load_employee: bool = True) -> List[ScheduleAssignment]:
    q = select(ScheduleAssignment).where(ScheduleAssignment.shift_id == shift_id).order_by(ScheduleAssignment.id)
    if load_employee:
        q = q.options(selectinload(ScheduleAssignment.employee))
    r = await db.execute(q)
    return list(r.scalars().all())


async def create_schedule_assignment(
    db: AsyncSession,
    shift_id: int,
    data: ScheduleAssignmentCreate,
) -> ScheduleAssignment:
    shift = await get_shift(db, shift_id)
    if not shift:
        raise ValueError("班別不存在")
    schedule = await get_schedule(db, shift.schedule_id)
    if not schedule:
        raise ValueError("排班表不存在")
    eligible = await is_employee_eligible_for_site_on_date(db, schedule.site_id, data.employee_id, shift.date)
    if not eligible:
        raise ScheduleAssignmentNotEligibleError("該員工在此班別日期不在案場有效指派期間內，無法排班")
    a = ScheduleAssignment(
        shift_id=shift_id,
        employee_id=data.employee_id,
        role=data.role,
        confirmed=data.confirmed,
        notes=data.notes,
    )
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return a


async def update_schedule_assignment(db: AsyncSession, a: ScheduleAssignment, data: ScheduleAssignmentUpdate) -> ScheduleAssignment:
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(a, k, v)
    await db.flush()
    await db.refresh(a)
    return a


async def delete_schedule_assignment(db: AsyncSession, a: ScheduleAssignment) -> None:
    await db.delete(a)


async def get_employee_monthly_shift_stats(
    db: AsyncSession,
    year_month: int,
    employee_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    產出月統計：員工在某月總班數、總工時、夜班數（供薪資/會計使用）。
    84-1 案場要能標記（is_84_1_site）。
    """
    year = year_month // 100
    month = year_month % 100
    if month == 0:
        month = 12
        year -= 1

    # 查詢該月所有 schedule_assignments，join shift -> schedule -> site
    q = (
        select(
            ScheduleAssignment.employee_id,
            ScheduleShift.id.label("shift_id"),
            ScheduleShift.date,
            ScheduleShift.shift_code,
            ScheduleShift.start_time,
            ScheduleShift.end_time,
            Schedule.site_id,
            Site.is_84_1,
        )
        .join(ScheduleShift, ScheduleAssignment.shift_id == ScheduleShift.id)
        .join(Schedule, ScheduleShift.schedule_id == Schedule.id)
        .join(Site, Schedule.site_id == Site.id)
        .where(Schedule.year == year, Schedule.month == month)
    )
    if employee_id is not None:
        q = q.where(ScheduleAssignment.employee_id == employee_id)
    r = await db.execute(q)
    rows = r.all()

    # 依 employee_id 彙總
    by_emp: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        eid = row.employee_id
        if eid not in by_emp:
            by_emp[eid] = {
                "employee_id": eid,
                "year_month": year_month,
                "total_shifts": 0,
                "total_hours": Decimal("0"),
                "night_shift_count": 0,
                "is_84_1_site": False,
                "site_ids": [],
            }
        by_emp[eid]["total_shifts"] += 1
        hrs = _shift_duration_hours(row.start_time, row.end_time)
        by_emp[eid]["total_hours"] += hrs
        if row.shift_code == "night":
            by_emp[eid]["night_shift_count"] += 1
        if row.is_84_1:
            by_emp[eid]["is_84_1_site"] = True
        if row.site_id not in by_emp[eid]["site_ids"]:
            by_emp[eid]["site_ids"].append(row.site_id)

    return list(by_emp.values())


# ---------- 傻瓜會計薪資結果 accounting_payroll_results ----------
# 刪除/查詢條件與寫入一致：year（西元）, month（1～12）, type（'security' 等，不可用中文）

async def count_payroll_results_for_period(
    db: AsyncSession, year: int, month: int, payroll_type: str
) -> int:
    """查詢指定年/月/類型的筆數（SELECT COUNT(*)）。"""
    r = await db.execute(
        select(func.count()).select_from(AccountingPayrollResult).where(
            AccountingPayrollResult.year == year,
            AccountingPayrollResult.month == month,
            AccountingPayrollResult.type == payroll_type,
        )
    )
    return r.scalar() or 0


async def delete_payroll_results_for_period(
    db: AsyncSession, year: int, month: int, payroll_type: str
) -> int:
    """刪除指定年/月/類型的已存結果，回傳刪除筆數。條件與寫入一致：year, month, type。"""
    r = await db.execute(
        delete(AccountingPayrollResult).where(
            AccountingPayrollResult.year == year,
            AccountingPayrollResult.month == month,
            AccountingPayrollResult.type == payroll_type,
        )
    )
    return r.rowcount or 0


async def save_payroll_results(
    db: AsyncSession,
    year: int,
    month: int,
    payroll_type: str,
    results: List[Dict[str, Any]],
) -> None:
    """儲存計算結果至 accounting_payroll_results（含應發/扣款/實發）。"""
    for row in results:
        db.add(
            AccountingPayrollResult(
                year=year,
                month=month,
                type=payroll_type,
                site=row.get("site", ""),
                employee=row.get("employee", ""),
                pay_type=row.get("pay_type"),
                total_hours=float(row.get("total_hours", 0)),
                gross_salary=row.get("gross_salary"),
                labor_insurance_employee=row.get("labor_insurance_employee"),
                health_insurance_employee=row.get("health_insurance_employee"),
                group_insurance=row.get("group_insurance"),
                self_pension_6=row.get("self_pension_6"),
                deductions_total=row.get("deductions_total"),
                net_salary=row.get("net_salary"),
                total_salary=float(row.get("total_salary", 0) or row.get("net_salary", 0)),
                status=row.get("status", ""),
            )
        )
    await db.flush()


async def get_payroll_results_for_period(
    db: AsyncSession, year: int, month: int, payroll_type: str
) -> List[Dict[str, Any]]:
    """查詢指定年/月/類型的薪資結果，回傳與前端表格一致的欄位。"""
    q = (
        select(AccountingPayrollResult)
        .where(
            AccountingPayrollResult.year == year,
            AccountingPayrollResult.month == month,
            AccountingPayrollResult.type == payroll_type,
        )
        .order_by(AccountingPayrollResult.site, AccountingPayrollResult.employee)
    )
    r = await db.execute(q)
    rows = r.scalars().all()
    return [
        {
            "site": row.site,
            "employee": row.employee,
            "pay_type": row.pay_type,
            "total_hours": row.total_hours,
            "gross_salary": row.gross_salary,
            "labor_insurance_employee": row.labor_insurance_employee,
            "health_insurance_employee": row.health_insurance_employee,
            "group_insurance": row.group_insurance,
            "self_pension_6": row.self_pension_6,
            "deductions_total": row.deductions_total,
            "net_salary": row.net_salary,
            "total_salary": row.total_salary,
            "status": row.status or "",
            "year": row.year,
            "month": row.month,
            "type": row.type,
        }
        for row in rows
    ]


def _normalize_lookup_text(value: Optional[str]) -> str:
    """姓名/案場比對用正規化：trim + 全形空白轉半形 + 壓縮連續空白。"""
    raw = (value or "").replace("\u3000", " ")
    return " ".join(raw.split())


def _pay_method_to_label(pay_method: Optional[str]) -> str:
    mapping = {
        "CASH": "領現",
        "SECURITY_FIRST": "保全一銀",
        "APARTMENT_FIRST": "公寓一銀",
        "SMITH_FIRST": "史密斯一銀",
        "OTHER_BANK": "其他銀行",
    }
    key = (pay_method or "").strip().upper()
    return mapping.get(key, "未設定")


def _empty_pay_stats() -> Dict[str, int]:
    return {
        "cash": 0,
        "sec_first": 0,
        "apt_first": 0,
        "smith_first": 0,
        "other_bank": 0,
        "unset": 0,
    }


def _add_pay_stats(stats: Dict[str, int], payment_method_label: str) -> None:
    if payment_method_label == "領現":
        stats["cash"] += 1
    elif payment_method_label == "保全一銀":
        stats["sec_first"] += 1
    elif payment_method_label == "公寓一銀":
        stats["apt_first"] += 1
    elif payment_method_label == "史密斯一銀":
        stats["smith_first"] += 1
    elif payment_method_label == "其他銀行":
        stats["other_bank"] += 1
    else:
        stats["unset"] += 1


async def enrich_history_records(
    db: AsyncSession,
    records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    將歷史薪資 records 動態補上員工領薪/銀行資訊，不回寫歷史表。
    優先匹配 (site + employee_name)，若無再 fallback employee_name。
    """
    stats = _empty_pay_stats()
    if not records:
        return [], stats

    raw_site_names = {(r.get("site") or "").strip() for r in records if (r.get("site") or "").strip()}
    raw_employee_names = {
        (r.get("employee") or "").strip()
        for r in records
        if (r.get("employee") or "").strip()
    }
    employee_names = {_normalize_lookup_text(v) for v in raw_employee_names}
    if not employee_names:
        enriched = []
        for row in records:
            out = dict(row)
            out.update(
                {
                    "salary_type": "未設定",
                    "bank_code": "",
                    "branch_code": "",
                    "account_number": "",
                    "conflict": False,
                    "matched_candidates_count": 0,
                }
            )
            _add_pay_stats(stats, "未設定")
            enriched.append(out)
        return enriched, stats

    site_rows = await db.execute(select(Site.id, Site.name).where(Site.name.in_(list(raw_site_names))))
    site_id_to_name_norm = {sid: _normalize_lookup_text(name) for sid, name in site_rows.all()}
    site_ids = list(site_id_to_name_norm.keys())

    emp_rows = await db.execute(
        select(
            Employee.id,
            Employee.name,
            Employee.pay_method,
            Employee.bank_code,
            Employee.branch_code,
            Employee.bank_account,
        ).where(Employee.name.in_(list(raw_employee_names)))
    )
    employees = emp_rows.all()

    name_candidates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for emp in employees:
        name_key = _normalize_lookup_text(emp.name)
        name_candidates[name_key].append(
            {
                "employee_id": emp.id,
                "name": emp.name,
                "pay_method": emp.pay_method,
                "bank_code": emp.bank_code,
                "branch_code": emp.branch_code,
                "bank_account": emp.bank_account,
            }
        )

    site_name_candidates: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    if site_ids:
        assign_rows = await db.execute(
            select(
                SiteEmployeeAssignment.site_id,
                Employee.id,
                Employee.name,
                Employee.pay_method,
                Employee.bank_code,
                Employee.branch_code,
                Employee.bank_account,
            )
            .join(Employee, SiteEmployeeAssignment.employee_id == Employee.id)
            .where(
                SiteEmployeeAssignment.site_id.in_(site_ids),
                Employee.name.in_(list(raw_employee_names)),
            )
        )
        for row in assign_rows.all():
            site_key = site_id_to_name_norm.get(row.site_id, "")
            if not site_key:
                continue
            emp_key = _normalize_lookup_text(row.name)
            site_name_candidates[(site_key, emp_key)].append(
                {
                    "employee_id": row.id,
                    "name": row.name,
                    "pay_method": row.pay_method,
                    "bank_code": row.bank_code,
                    "branch_code": row.branch_code,
                    "bank_account": row.bank_account,
                }
            )

    enriched: List[Dict[str, Any]] = []
    for record in records:
        out = dict(record)
        site_key = _normalize_lookup_text(record.get("site"))
        emp_key = _normalize_lookup_text(record.get("employee"))
        candidates = site_name_candidates.get((site_key, emp_key), [])
        if not candidates:
            candidates = name_candidates.get(emp_key, [])

        matched_candidates_count = len(candidates)
        conflict = matched_candidates_count > 1

        payment_method_label = "未設定"
        bank_code = ""
        branch_code = ""
        account_number = ""
        if matched_candidates_count == 1:
            matched = candidates[0]
            payment_method_label = _pay_method_to_label(matched.get("pay_method"))
            if payment_method_label not in ("領現", "未設定"):
                bank_code = (matched.get("bank_code") or "").strip()
                branch_code = (matched.get("branch_code") or "").strip()
                account_number = (matched.get("bank_account") or "").strip()

        _add_pay_stats(stats, payment_method_label)
        out.update(
            {
                "salary_type": payment_method_label,
                "bank_code": bank_code,
                "branch_code": branch_code,
                "account_number": account_number,
                "conflict": conflict,
                "matched_candidates_count": matched_candidates_count,
            }
        )
        enriched.append(out)

    return enriched, stats


async def get_payroll_history_months(
    db: AsyncSession, payroll_type: str = "security"
) -> List[Dict[str, int]]:
    """回傳已存檔的 (year, month) 列表，供前端下拉選單。"""
    r = await db.execute(
        select(AccountingPayrollResult.year, AccountingPayrollResult.month)
        .where(AccountingPayrollResult.type == payroll_type)
        .distinct()
        .order_by(AccountingPayrollResult.year.desc(), AccountingPayrollResult.month.desc())
    )
    rows = r.all()
    return [{"year": y, "month": m} for y, m in rows]
