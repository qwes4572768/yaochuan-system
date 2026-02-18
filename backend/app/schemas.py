"""API 請求/回應結構 - Pydantic（依規格 Employee / Dependent）"""
from datetime import date, datetime, time
from decimal import Decimal

# 別名：欄位名 date 與型別 date 會觸發 Pydantic 的 field name clashing，改用 DateType 註解
DateType = date
from typing import Optional, List, Dict
import re
from pydantic import BaseModel, Field, ConfigDict, validator, field_validator, model_validator


# 身分證字號格式：台灣舊式 1 字母+9 數字 或 新式 2 字母+8 數字
NATIONAL_ID_PATTERN = re.compile(r"^[A-Za-z]\d{9}$|^[A-Za-z]{2}\d{8}$")


def validate_national_id(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().upper()
    if len(v) != 10:
        raise ValueError("身分證字號應為 10 碼")
    if not NATIONAL_ID_PATTERN.match(v):
        raise ValueError("身分證字號格式錯誤（例：A123456789 或 AB12345678）")
    return v


def validate_national_id_or_masked(v: Optional[str]) -> Optional[str]:
    """接受完整身分證或遮罩後字串（如 S1****9788），供 API 回傳用"""
    if not v:
        return v
    v = v.strip()
    if "*" in v:
        return v
    return validate_national_id(v)


# ---------- 眷屬 ----------
class DependentBase(BaseModel):
    name: str = Field(..., description="姓名")
    birth_date: Optional[date] = None
    national_id: Optional[str] = None
    relation: str = Field(..., description="配偶/子女/父母/祖父母/其他")
    city: Optional[str] = None
    is_disabled: bool = False
    disability_level: Optional[str] = None
    notes: Optional[str] = None


class DependentCreate(DependentBase):
    @validator("national_id")
    def check_national_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_national_id(v) if v else v


class DependentUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    national_id: Optional[str] = None
    relation: Optional[str] = None
    city: Optional[str] = None
    is_disabled: Optional[bool] = None
    disability_level: Optional[str] = None
    notes: Optional[str] = None

    @validator("national_id")
    def check_national_id(cls, v: Optional[str]) -> Optional[str]:
        reject_masked_value("眷屬身分證字號", v)
        return validate_national_id(v) if v else v


class DependentRead(DependentBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @validator("national_id", pre=True)
    def allow_masked_national_id(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if "*" in str(v):
            return v
        return validate_national_id(v)


# ---------- 員工 ----------
PAY_METHOD_CHOICES = {"SECURITY_FIRST", "APARTMENT_FIRST", "SMITH_FIRST", "CASH", "OTHER_BANK"}
PROPERTY_PAY_MODE_CHOICES = {"WEEKLY_2H", "MONTHLY_8H_HOLIDAY"}
COMPANY_PAY_MODE_CHOICES = {"monthly", "hourly", "daily"}


class EmployeeBase(BaseModel):
    name: str = Field(..., description="姓名（必填）")
    birth_date: date = Field(..., description="出生年月日（必填）")
    national_id: str = Field(..., description="身分證字號（必填）")
    reg_address: str = Field(..., description="戶籍地址（必填）")
    live_address: str = Field(..., description="居住地址（必填）")
    live_same_as_reg: bool = False
    salary_type: Optional[str] = Field(None, description="月薪/日薪/時薪")
    salary_value: Optional[Decimal] = None
    insured_salary_level: Optional[Decimal] = Field(None, description="投保薪資級距（下拉選級距）")
    enroll_date: Optional[date] = None
    cancel_date: Optional[date] = None
    dependent_count: int = Field(0, ge=0, description="眷屬數量 0~N")
    pension_self_6: bool = Field(False, description="員工自提6%（試算/結算帶入）")
    registration_type: str = Field("security", description="登載身份：security=保全、property=物業、smith=史密斯、lixiang=立翔人力")
    notes: Optional[str] = None
    pay_method: str = Field("CASH", description="領薪方式：SECURITY_FIRST/APARTMENT_FIRST/SMITH_FIRST/CASH/OTHER_BANK")
    bank_code: Optional[str] = Field(None, description="銀行代碼（3 碼，僅非 CASH 時必填）")
    branch_code: Optional[str] = Field(None, description="分行代碼（4 碼，僅非 CASH 時必填）")
    bank_account: Optional[str] = Field(None, description="銀行帳號（6～20 碼，僅非 CASH 時必填）")
    property_pay_mode: Optional[str] = Field(None, description="物業計薪模式：monthly/hourly/daily（相容舊值 WEEKLY_2H/MONTHLY_8H_HOLIDAY）")
    security_pay_mode: Optional[str] = Field(None, description="保全計薪模式：monthly/hourly/daily")
    smith_pay_mode: Optional[str] = Field(None, description="史密斯計薪模式：monthly/hourly/daily")
    lixiang_pay_mode: Optional[str] = Field(None, description="立翔人力計薪模式：monthly/hourly/daily")
    weekly_amount: Optional[Decimal] = Field(None, description="物業每週完成給付金額（僅 WEEKLY_2H 使用）")
    property_salary: Optional[Decimal] = Field(None, description="物業固定月薪（僅 payroll_type=property 使用）")

    @validator("pay_method")
    def validate_pay_method(cls, v: str) -> str:
        v = (v or "CASH").strip()
        if v not in PAY_METHOD_CHOICES:
            raise ValueError("領薪方式無效")
        return v

    @validator("bank_code", "branch_code", "bank_account", pre=True)
    def strip_empty_bank_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @validator("property_pay_mode")
    def validate_property_pay_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        raw = v.strip()
        if not raw:
            return None
        lower_value = raw.lower()
        if lower_value in COMPANY_PAY_MODE_CHOICES:
            return lower_value
        value = raw.upper()
        if not value:
            return None
        if value not in PROPERTY_PAY_MODE_CHOICES:
            raise ValueError("物業計薪模式無效")
        return value

    @validator("security_pay_mode", "smith_pay_mode", "lixiang_pay_mode")
    def validate_company_pay_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip().lower()
        if not value:
            return None
        if value not in COMPANY_PAY_MODE_CHOICES:
            raise ValueError("公司別計薪模式無效")
        return value


class EmployeeCreate(EmployeeBase):
    dependents: Optional[List[DependentCreate]] = None

    @validator("national_id")
    def check_national_id(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            raise ValueError("身分證字號為必填")
        return validate_national_id(v)

    @model_validator(mode="after")
    def validate_pay_method_and_bank(self) -> "EmployeeCreate":
        pm = self.pay_method
        bc = self.bank_code or None
        br = self.branch_code or None
        acc = self.bank_account or None
        # 禁止遮罩值
        for label, val in [("銀行代碼", bc), ("分行代碼", br), ("銀行帳號", acc)]:
            reject_masked_value(label, val)
        if pm == "CASH":
            # 領現：三欄必須為空（由後端視為 None）
            self.bank_code = None
            self.branch_code = None
            self.bank_account = None
            return self
        # 非 CASH：三欄必填且格式須為數字
        if not bc or not br or not acc:
            raise ValueError("非領現時，銀行代碼/分行代碼/銀行帳號皆為必填")
        if not bc.isdigit() or len(bc) != 3:
            raise ValueError("銀行代碼須為 3 碼數字")
        if not br.isdigit() or len(br) != 4:
            raise ValueError("分行代碼須為 4 碼數字")
        if not acc.isdigit() or not (6 <= len(acc) <= 20):
            raise ValueError("銀行帳號須為 6～20 碼數字")
        return self


def reject_masked_value(field_name: str, v: Optional[str]) -> Optional[str]:
    """禁止將遮罩值寫回 DB（僅接受完整原始值）。"""
    if not v:
        return v
    if "*" in v:
        raise ValueError(f"{field_name}不可為遮罩值，請填寫完整資料")
    return v


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    national_id: Optional[str] = None
    reg_address: Optional[str] = None
    live_address: Optional[str] = None
    live_same_as_reg: Optional[bool] = None
    salary_type: Optional[str] = None
    salary_value: Optional[Decimal] = None
    insured_salary_level: Optional[Decimal] = None
    enroll_date: Optional[date] = None
    cancel_date: Optional[date] = None
    dependent_count: Optional[int] = Field(None, ge=0)
    pension_self_6: Optional[bool] = None
    registration_type: Optional[str] = None
    notes: Optional[str] = None
    pay_method: Optional[str] = None
    bank_code: Optional[str] = None
    branch_code: Optional[str] = None
    bank_account: Optional[str] = None
    property_pay_mode: Optional[str] = None
    security_pay_mode: Optional[str] = None
    smith_pay_mode: Optional[str] = None
    lixiang_pay_mode: Optional[str] = None
    weekly_amount: Optional[Decimal] = None
    property_salary: Optional[Decimal] = None

    @validator("national_id")
    def check_national_id(cls, v: Optional[str]) -> Optional[str]:
        reject_masked_value("身分證字號", v)
        return validate_national_id(v) if v else v

    @validator("reg_address")
    def check_reg_address(cls, v: Optional[str]) -> Optional[str]:
        return reject_masked_value("戶籍地址", v)

    @validator("live_address")
    def check_live_address(cls, v: Optional[str]) -> Optional[str]:
        return reject_masked_value("居住地址", v)

    @validator("pay_method")
    def validate_pay_method_update(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if v not in PAY_METHOD_CHOICES:
            raise ValueError("領薪方式無效")
        return v

    @validator("property_pay_mode")
    def validate_property_pay_mode_update(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        raw = v.strip()
        if not raw:
            return None
        lower_value = raw.lower()
        if lower_value in COMPANY_PAY_MODE_CHOICES:
            return lower_value
        value = raw.upper()
        if not value:
            return None
        if value not in PROPERTY_PAY_MODE_CHOICES:
            raise ValueError("物業計薪模式無效")
        return value

    @validator("security_pay_mode", "smith_pay_mode", "lixiang_pay_mode")
    def validate_company_pay_mode_update(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip().lower()
        if not value:
            return None
        if value not in COMPANY_PAY_MODE_CHOICES:
            raise ValueError("公司別計薪模式無效")
        return value

    @validator("bank_code", "branch_code", "bank_account")
    def validate_bank_fields_masked(cls, v: Optional[str]) -> Optional[str]:
        # 先阻擋遮罩值，數字/長度驗證在 model_validator 中處理（有 pay_method 與其他欄位可一起檢查）
        return reject_masked_value("銀行欄位", v)

    @model_validator(mode="after")
    def validate_pay_method_and_bank_update(self) -> "EmployeeUpdate":
        pm = self.pay_method
        bc = self.bank_code or None
        br = self.branch_code or None
        acc = self.bank_account or None
        # 若前端送的是完整表單，則與 EmployeeCreate 規則相同；若是部分欄位，僅在 pay_method 或任一銀行欄位出現時檢查一致性
        touched_bank = any(v is not None for v in (bc, br, acc))
        if pm is None and not touched_bank:
            return self
        effective_pm = pm or "CASH"
        if effective_pm == "CASH":
            if touched_bank and any(v for v in (bc, br, acc)):
                raise ValueError("領現時不得填寫銀行代碼/分行代碼/銀行帳號")
            self.bank_code = None
            self.branch_code = None
            self.bank_account = None
            return self
        # 非 CASH：若有任一銀行欄位被送出，就要求三者皆存在且格式正確
        if touched_bank or pm is not None:
            if not bc or not br or not acc:
                raise ValueError("非領現時，銀行代碼/分行代碼/銀行帳號皆為必填")
            if not bc.isdigit() or len(bc) != 3:
                raise ValueError("銀行代碼須為 3 碼數字")
            if not br.isdigit() or len(br) != 4:
                raise ValueError("分行代碼須為 4 碼數字")
            if not acc.isdigit() or not (6 <= len(acc) <= 20):
                raise ValueError("銀行帳號須為 6～20 碼數字")
        return self


class EmployeeRead(EmployeeBase):
    id: int
    safety_pdf_path: Optional[str] = None
    contract_84_1_pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    dependents: List[DependentRead] = []
    model_config = ConfigDict(from_attributes=True)

    @validator("national_id", pre=True)
    def allow_masked_national_id(cls, v: Optional[str]) -> Optional[str]:
        """API 回傳可為遮罩（S1****9788），不驗格式"""
        if not v:
            return v
        if "*" in str(v):
            return v
        return validate_national_id(v)


class EmployeeListBrief(BaseModel):
    id: int
    name: str
    birth_date: Optional[date] = None
    insured_salary_level: Optional[Decimal] = None
    enroll_date: Optional[date] = None
    dependent_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# ---------- 級距（供前端下拉） ----------
class SalaryBracketItem(BaseModel):
    level: Decimal = Field(..., description="級距金額")
    low: int = Field(..., description="薪資下限")
    high: int = Field(..., description="薪資上限")


# ---------- 檔案 ----------
class DocumentRead(BaseModel):
    id: int
    employee_id: int
    document_type: str
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- 費用試算 ----------
class InsuranceEstimateRequest(BaseModel):
    employee_id: Optional[int] = None
    insured_salary_level: Optional[Decimal] = None
    dependent_count: int = 0
    year: Optional[int] = None
    month: Optional[int] = None
    pension_self_6: bool = Field(False, description="是否啟用員工自提6%（金額取自級距表同列 labor_pension）")


class ItemBreakdown(BaseModel):
    name: str
    employer: Decimal = Decimal("0")
    employee: Decimal = Decimal("0")
    total: Decimal = Decimal("0")


# 健保明細：原本個人負擔 vs 減免後個人負擔 vs 公司負擔（規則集中於 rules 模組）
class HealthInsuranceDetailRow(BaseModel):
    name: str = Field(..., description="姓名")
    role: str = Field(..., description="本人 或 眷屬")
    rule_applied: List[str] = Field(default_factory=list, description="套用之減免規則名稱")
    original_personal: Decimal = Field(..., description="原本個人負擔")
    reduced_personal: Decimal = Field(..., description="減免後個人負擔")


class HealthInsuranceBreakdown(BaseModel):
    original_personal_total: Decimal = Field(..., description="原本個人負擔合計")
    reduced_personal_total: Decimal = Field(..., description="減免後個人負擔合計")
    employer_total: Decimal = Field(..., description="公司負擔（不因減免變動）")
    detail: List[HealthInsuranceDetailRow] = Field(default_factory=list, description="每人明細")


class InsuranceEstimateResponse(BaseModel):
    insured_salary_level: Decimal
    labor_insurance: ItemBreakdown
    health_insurance: ItemBreakdown
    health_insurance_breakdown: Optional[HealthInsuranceBreakdown] = Field(None, description="健保分攤/減免明細（有員工+眷屬資料時才有）")
    occupational_accident: ItemBreakdown
    labor_pension: ItemBreakdown
    group_insurance: ItemBreakdown
    pension_self_6: Optional[ItemBreakdown] = Field(None, description="員工自提6%（勾選時才有；employer=0, employee=級距表 labor_pension）")
    total_employer: Decimal
    total_employee: Decimal
    total: Decimal
    dependent_count: int
    from_excel: bool = Field(False, description="true 表示本結果來自 Excel 試算檔，公司/員工/合計以 Excel 為準")
    insured_days: Optional[int] = Field(None, description="當月加保天數（有依加退保日按比例計費時才有）")
    billing_note: Optional[str] = Field(None, description="計費說明，例如：勞保/職災/勞退按天數比例；健保當月整月或當月不計")
    calculation_steps: Optional[List[Dict[str, str]]] = Field(None, description="計算過程（項目與公式說明），供前端顯示；Excel 試算時為空")
    from_bracket_table: bool = Field(False, description="true 表示本結果來自級距表查表（權威資料）")
    bracket_source: Optional[Dict[str, str]] = Field(None, description="級距表來源：file_name, imported_at（僅當 from_bracket_table 時有值）")


# ---------- 級距表 rate_tables / rate_items ----------
class RateItemBase(BaseModel):
    level_name: Optional[str] = None
    salary_min: Decimal = Decimal("0")
    salary_max: Decimal = Decimal("0")
    insured_salary: Optional[Decimal] = None
    employee_rate: Decimal = Decimal("0")
    employer_rate: Decimal = Decimal("0")
    gov_rate: Optional[Decimal] = None
    fixed_amount_if_any: Optional[Decimal] = None


class RateItemRead(RateItemBase):
    id: int
    table_id: int
    model_config = ConfigDict(from_attributes=True)


class RateTableBase(BaseModel):
    type: str = Field(..., description="labor_insurance / health_insurance / occupational_accident / labor_pension")
    version: str = Field(..., description="版本代碼，如 2025-01")
    effective_from: date = Field(..., description="生效起日（含）")
    effective_to: Optional[date] = None
    total_rate: Optional[Decimal] = None
    note: Optional[str] = None


class RateTableRead(RateTableBase):
    id: int
    items: List[RateItemRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class RateTableImportItem(BaseModel):
    level_name: Optional[str] = None
    salary_min: int | Decimal
    salary_max: int | Decimal
    insured_salary: Optional[int | Decimal] = None
    employee_rate: float | Decimal = 0
    employer_rate: float | Decimal = 0
    gov_rate: Optional[float | Decimal] = None
    fixed_amount_if_any: Optional[float | Decimal] = None


class RateTableImportTable(BaseModel):
    type: str
    version: str
    effective_from: str
    effective_to: Optional[str] = None
    total_rate: Optional[float] = None
    note: Optional[str] = None
    items: List[RateTableImportItem] = Field(default_factory=list)


class RateTableImportPayload(BaseModel):
    tables: List[RateTableImportTable] = Field(default_factory=list)


# ---------- 薪資設定 salary_profile（第二階段排班/會計用） ----------
class SalaryProfileBase(BaseModel):
    salary_type: str = Field(..., description="月薪/日薪/時薪")
    monthly_base: Optional[Decimal] = None
    daily_rate: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    overtime_eligible: bool = False
    calculation_rules: Optional[str] = None


class SalaryProfileRead(SalaryProfileBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SalaryProfileUpdate(SalaryProfileBase):
    pass


# ---------- 保險結果落表 insurance_monthly_result（會計抓 company cost） ----------
class InsuranceMonthlyResultRead(BaseModel):
    id: int
    employee_id: int
    year_month: int = Field(..., description="西元年月，如 202501")
    item_type: str = Field(..., description="labor_insurance / health_insurance / occupational_accident / labor_pension / group_insurance")
    employee_amount: Decimal = Decimal("0")
    employer_amount: Decimal = Decimal("0")
    gov_amount: Optional[Decimal] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- 案場管理 sites / site_employee_assignments ----------
# 服務類型多選值（前端顯示用）
SERVICE_TYPE_OPTIONS = ["駐衛保全服務", "公寓大廈管理服務", "保全綜合服務"]
SITE_TYPE_OPTIONS = ["community", "factory"]  # 社區 / 工廠


class SiteBase(BaseModel):
    name: str = Field(..., description="案場名稱")
    address: str = Field(..., description="案場地址")
    contract_start: date = Field(..., description="合約起始日")
    contract_end: Optional[date] = None
    # 既有欄位（排班/指派相容，可與新欄位二擇一填寫）
    client_name: Optional[str] = Field(None, description="客戶名稱（相容用，可填 customer_name）")
    monthly_amount: Optional[Decimal] = Field(None, description="每月合約金額（相容用，可填 monthly_fee_incl_tax）")
    payment_method: Optional[str] = Field(None, description="收款方式：transfer / cash / check")
    receivable_day: Optional[int] = Field(None, ge=1, le=31, description="每月應收日 1-31")
    notes: Optional[str] = None
    daily_required_count: Optional[int] = Field(None, ge=0, description="每日需要人數")
    shift_hours: Optional[Decimal] = Field(None, description="每班別工時，如 8 / 12")
    is_84_1: bool = Field(False, description="是否屬於 84-1 案場")
    night_shift_allowance: Optional[Decimal] = None
    bear_labor_insurance: bool = Field(True, description="此案場是否需負擔勞保公司負擔")
    bear_health_insurance: bool = Field(True, description="此案場是否需負擔健保公司負擔")
    has_group_or_occupational: bool = Field(False, description="此案場是否有團保或職災保費")
    rebate_type: Optional[str] = Field(None, description="案場回饋：amount / percent")
    rebate_value: Optional[Decimal] = None
    # 案場管理擴充欄位
    site_type: Optional[str] = Field(None, description="案場類型：community / factory")
    service_types: Optional[str] = Field(None, description="服務類型 JSON 陣列字串，如 [\"駐衛保全服務\",\"公寓大廈管理服務\"]")
    monthly_fee_excl_tax: Optional[Decimal] = Field(None, description="月服務費未稅")
    tax_rate: Optional[Decimal] = Field(None, description="稅率 如 0.05")
    monthly_fee_incl_tax: Optional[Decimal] = Field(None, description="月服務費含稅")
    invoice_due_day: Optional[int] = Field(None, ge=1, le=31, description="每月發票期限日 1-31")
    payment_due_day: Optional[int] = Field(None, ge=1, le=31, description="每月收款期限日 1-31")
    remind_days: Optional[int] = Field(None, description="契約到期提醒天數，預設 30")
    customer_name: Optional[str] = Field(None, description="客戶名稱（開票與聯絡）")
    customer_tax_id: Optional[str] = Field(None, description="統一編號")
    customer_contact: Optional[str] = Field(None, description="聯絡人")
    customer_phone: Optional[str] = Field(None, description="電話")
    customer_email: Optional[str] = Field(None, description="Email")
    invoice_title: Optional[str] = Field(None, description="發票抬頭")
    invoice_mail_address: Optional[str] = Field(None, description="發票郵寄地址")
    invoice_receiver: Optional[str] = Field(None, description="收件人")


class SiteCreate(SiteBase):
    """新增案場時，若未填 client_name/monthly_amount/payment_method/receivable_day 則由 customer_name/monthly_fee_incl_tax/payment_due_day 推導。"""
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    client_name: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    monthly_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    receivable_day: Optional[int] = Field(None, ge=1, le=31)
    notes: Optional[str] = None
    daily_required_count: Optional[int] = Field(None, ge=0)
    shift_hours: Optional[Decimal] = None
    is_84_1: Optional[bool] = None
    night_shift_allowance: Optional[Decimal] = None
    bear_labor_insurance: Optional[bool] = None
    bear_health_insurance: Optional[bool] = None
    has_group_or_occupational: Optional[bool] = None
    rebate_type: Optional[str] = None
    rebate_value: Optional[Decimal] = None
    site_type: Optional[str] = None
    service_types: Optional[str] = None
    monthly_fee_excl_tax: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    monthly_fee_incl_tax: Optional[Decimal] = None
    invoice_due_day: Optional[int] = Field(None, ge=1, le=31)
    payment_due_day: Optional[int] = Field(None, ge=1, le=31)
    remind_days: Optional[int] = None
    customer_name: Optional[str] = None
    customer_tax_id: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    invoice_title: Optional[str] = None
    invoice_mail_address: Optional[str] = None
    invoice_receiver: Optional[str] = None


class SiteRead(SiteBase):
    id: int
    is_active: Optional[bool] = Field(True, description="是否有效（false=已移除或已歸檔）")
    deactivated_at: Optional[datetime] = None
    deactivated_reason: Optional[str] = None
    is_archived: Optional[bool] = Field(False, description="是否為歷史案場（到期未續約）")
    archived_at: Optional[datetime] = None
    archived_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @validator("tax_rate", pre=True, always=True)
    def serialize_tax_rate(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return v if v is not None else Decimal("0.05")

    @validator("remind_days", pre=True, always=True)
    def serialize_remind_days(cls, v: Optional[int]) -> Optional[int]:
        return v if v is not None else 30


class SiteListItem(BaseModel):
    """案場列表單筆（含計算欄位：到期天數、狀態、本月應收、本月是否入帳、是否已移除）"""
    id: int
    name: str
    address: Optional[str] = None
    site_type: Optional[str] = None
    service_types: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    monthly_fee_excl_tax: Optional[Decimal] = None
    monthly_fee_incl_tax: Optional[Decimal] = None
    invoice_due_day: Optional[int] = None
    payment_due_day: Optional[int] = None
    client_name: Optional[str] = None
    customer_name: Optional[str] = None
    # 計算欄位
    days_to_expire: Optional[int] = Field(None, description="距契約到期天數（負數表已到期）")
    status: Optional[str] = Field(None, description="normal / expiring / expired / inactive")
    current_month_expected_amount: Optional[Decimal] = Field(None, description="本月應收金額")
    current_month_received: Optional[bool] = Field(None, description="本月是否已入帳")
    is_active: Optional[bool] = Field(True, description="是否有效（false=已移除或已歸檔）")
    is_archived: Optional[bool] = Field(False, description="是否為歷史案場（到期未續約）")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SiteListResponse(BaseModel):
    """案場列表分頁回傳（案場管理用，含 status / 本月應收等）"""
    items: List[SiteListItem] = Field(default_factory=list, description="本頁案場列表")
    total: int = Field(..., description="符合條件的總筆數")
    page: int = Field(..., ge=1, description="目前頁碼")
    page_size: int = Field(..., ge=1, le=500, description="每頁筆數")


class SiteAssignmentBase(BaseModel):
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class SiteAssignmentCreate(SiteAssignmentBase):
    employee_id: int = Field(..., description="員工 ID")


class SiteAssignmentUpdate(BaseModel):
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class SiteAssignmentRead(SiteAssignmentBase):
    id: int
    site_id: int
    employee_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SiteAssignmentWithEmployee(SiteAssignmentRead):
    """指派紀錄含員工簡要（姓名等）"""
    employee_name: Optional[str] = None


class SiteAssignmentWithSite(SiteAssignmentRead):
    """指派紀錄含案場簡要"""
    site_name: Optional[str] = None
    site_client_name: Optional[str] = None


# ---------- 案場回饋 site_rebates ----------
class SiteRebateBase(BaseModel):
    item_name: str = Field(..., description="回饋項目名稱")
    is_completed: bool = Field(False, description="是否已完成")
    completed_date: Optional[date] = None
    cost_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class SiteRebateCreate(SiteRebateBase):
    pass


class SiteRebateUpdate(BaseModel):
    item_name: Optional[str] = None
    is_completed: Optional[bool] = None
    completed_date: Optional[date] = None
    cost_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class SiteRebateRead(SiteRebateBase):
    id: int
    site_id: int
    receipt_pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- 案場每月入帳 site_monthly_receipts ----------
class SiteMonthlyReceiptBase(BaseModel):
    billing_month: str = Field(..., description="YYYY-MM")
    expected_amount: Optional[Decimal] = None
    is_received: bool = Field(False, description="是否已入帳")
    received_date: Optional[date] = None
    received_amount: Optional[Decimal] = None
    payment_method: Optional[str] = Field(None, description="transfer/cash/check/other")
    notes: Optional[str] = None


class SiteMonthlyReceiptCreate(SiteMonthlyReceiptBase):
    pass


class SiteMonthlyReceiptBatchCreate(BaseModel):
    """一鍵產生指定年度 1～12 月入帳紀錄（expected_amount 預設帶入案場月費含稅）"""
    year: int = Field(..., description="年度，例如 2026")


class SiteMonthlyReceiptUpdate(BaseModel):
    expected_amount: Optional[Decimal] = None
    is_received: Optional[bool] = None
    received_date: Optional[date] = None
    received_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class SiteMonthlyReceiptRead(SiteMonthlyReceiptBase):
    id: int
    site_id: int
    proof_pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- 排班 P0：schedules / schedule_shifts / schedule_assignments ----------
class ScheduleBase(BaseModel):
    site_id: int = Field(..., description="案場 ID")
    year: int = Field(..., description="年度")
    month: int = Field(..., ge=1, le=12, description="月份 1-12")
    status: str = Field("draft", description="draft / published / locked")
    notes: Optional[str] = None


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class ScheduleRead(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScheduleShiftBase(BaseModel):
    date: DateType = Field(..., description="班別日期")
    shift_code: str = Field(..., description="日 day / 夜 night / 保留 reserved")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    required_headcount: int = Field(1, ge=0, description="需求人數")


class ScheduleShiftCreate(ScheduleShiftBase):
    pass


class ScheduleShiftUpdate(BaseModel):
    date: Optional[DateType] = None
    shift_code: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    required_headcount: Optional[int] = Field(None, ge=0)


class ScheduleShiftRead(ScheduleShiftBase):
    id: int
    schedule_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScheduleShiftBatchCreate(BaseModel):
    """批量建立一整月班別：依 shift_code 與 start/end 模板，為該月每一天建立一筆 shift。"""
    shift_code: str = Field(..., description="day / night / reserved")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    required_headcount: int = Field(1, ge=0)


class ScheduleAssignmentBase(BaseModel):
    employee_id: int = Field(..., description="員工 ID")
    role: str = Field("normal", description="隊長 leader / 哨點 post / 一般 normal")
    confirmed: bool = False
    notes: Optional[str] = None


class ScheduleAssignmentCreate(ScheduleAssignmentBase):
    pass


class ScheduleAssignmentUpdate(BaseModel):
    role: Optional[str] = None
    confirmed: Optional[bool] = None
    notes: Optional[str] = None


class ScheduleAssignmentRead(ScheduleAssignmentBase):
    id: int
    shift_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScheduleAssignmentWithEmployee(ScheduleAssignmentRead):
    """指派含員工姓名"""
    employee_name: Optional[str] = None


class EmployeeMonthlyShiftStats(BaseModel):
    """員工某月排班統計：總班數、總工時、夜班數（供薪資/會計使用）。"""
    employee_id: int = Field(..., description="員工 ID")
    year_month: int = Field(..., description="西元年月，如 202501")
    total_shifts: int = Field(0, description="總班數")
    total_hours: Decimal = Field(Decimal("0"), description="總工時")
    night_shift_count: int = Field(0, description="夜班數")
    is_84_1_site: bool = Field(False, description="是否含 84-1 案場班次")
    site_ids: List[int] = Field(default_factory=list, description="有排班的案場 ID 列表")


# ---------- 巡邏管理 patrol ----------
class DeviceFingerprintPayload(BaseModel):
    userAgent: str = ""
    platform: str = ""
    browser: str = ""
    language: str = ""
    screen: str = ""
    timezone: str = ""
    ip: Optional[str] = None


class PatrolBindingCodeCreate(BaseModel):
    expire_minutes: int = Field(10, ge=1, le=60, description="綁定碼有效分鐘數")


class PatrolBindingCodeRead(BaseModel):
    code: str
    expires_at: datetime
    bind_url: str
    qr_value: str


class PatrolBindRequest(BaseModel):
    code: str
    employee_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=128)
    site_name: str = Field(..., min_length=1, max_length=120)
    device_fingerprint: DeviceFingerprintPayload


class PatrolBindResponse(BaseModel):
    device_token: str
    employee_name: str
    site_name: str
    bound_at: datetime


class PatrolDeviceRead(BaseModel):
    id: int
    employee_name: str
    site_name: str
    is_active: bool
    password_set: bool = True
    bound_at: datetime
    unbound_at: Optional[datetime] = None
    device_fingerprint: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PatrolBoundLoginRequest(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=128)
    device_fingerprint: DeviceFingerprintPayload


class PatrolBoundLoginResponse(BaseModel):
    device_token: str
    employee_name: str
    site_name: str
    bound_at: datetime


class PatrolUnbindRequest(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=128)
    device_fingerprint: DeviceFingerprintPayload


class PatrolUnbindResponse(BaseModel):
    success: bool
    message: str
    unbound_at: datetime


class PatrolBindingStatusResponse(BaseModel):
    is_bound: bool
    employee_name: Optional[str] = None
    site_name: Optional[str] = None
    ua: Optional[str] = None
    platform: Optional[str] = None
    browser: Optional[str] = None
    language: Optional[str] = None
    screen: Optional[str] = None
    timezone: Optional[str] = None
    password_set: bool = False
    bound_at: Optional[datetime] = None


class PatrolPointBase(BaseModel):
    point_code: str = Field(..., min_length=1, max_length=80)
    point_name: str = Field(..., min_length=1, max_length=120)
    site_id: Optional[int] = None
    site_name: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class PatrolPointCreate(BaseModel):
    point_code: str = Field(..., min_length=1, max_length=80)
    point_name: Optional[str] = Field(None, min_length=1, max_length=120)
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    site_id: Optional[int] = None
    site_name: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class PatrolPointUpdate(BaseModel):
    point_code: Optional[str] = Field(None, min_length=1, max_length=80)
    point_name: Optional[str] = Field(None, min_length=1, max_length=120)
    site_id: Optional[int] = None
    site_name: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class PatrolPointRead(PatrolPointBase):
    id: int
    public_id: str
    qr_url: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PatrolPointQrRead(BaseModel):
    public_id: str
    point_code: str
    qr_url: str
    qr_value: str


class PatrolCheckinRequest(BaseModel):
    qr_value: str = Field(..., min_length=1, max_length=1000)


class PatrolPublicCheckinRequest(BaseModel):
    employee_id: Optional[int] = None
    employee_name: Optional[str] = Field(None, min_length=1, max_length=80)
    timestamp: Optional[datetime] = None
    device_info: Optional[str] = None


class PatrolCheckinResponse(BaseModel):
    id: int
    employee_id: Optional[int] = None
    employee_name: str
    site_name: str
    point_code: str
    point_name: str
    checkin_date: date
    checkin_time: time
    checkin_ampm: str
    created_at: datetime


class PatrolLogRead(BaseModel):
    id: int
    employee_name: str
    site_name: str
    point_code: str
    point_name: str
    checkin_date: date
    checkin_time: time
    checkin_ampm: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
