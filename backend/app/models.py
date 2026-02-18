"""資料庫模型 - HR 人事管理（依規格：Employee / Dependent 欄位）。
第二階段預留：employee_id 永久不變（不可用姓名當 key）；薪資由 salary_profile 擴充；保險結果落表 insurance_monthly_result 供會計抓 company cost。"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Date, Time, Text, Numeric, ForeignKey, DateTime, Boolean, Integer, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Employee(Base):
    """員工基本資料。employee_id (id) 永久不變，不可用姓名當 key。"""
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="employee_id 永久不變，不可用姓名當 key")
    name: Mapped[str] = mapped_column(String(50), comment="姓名（必填）")
    birth_date: Mapped[date] = mapped_column(Date, comment="出生年月日（必填）")
    national_id: Mapped[str] = mapped_column(String(500), comment="身分證字號（必填、加密或明碼）")
    reg_address: Mapped[str] = mapped_column(String(500), comment="戶籍地址（必填）")
    live_address: Mapped[str] = mapped_column(String(500), comment="居住地址（必填）")
    live_same_as_reg: Mapped[bool] = mapped_column(Boolean, default=False, comment="居住同戶籍")
    # 薪資：月薪/日薪/時薪 + 數值（至少一個）
    salary_type: Mapped[Optional[str]] = mapped_column(String(20), comment="月薪/日薪/時薪")
    salary_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="薪資數值")
    # 加保投保薪資（級距，下拉或輸入金額對應）
    insured_salary_level: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 0), comment="投保薪資級距")
    enroll_date: Mapped[Optional[date]] = mapped_column(Date, comment="加保日期")
    cancel_date: Mapped[Optional[date]] = mapped_column(Date, comment="退保日期（可空）")
    dependent_count: Mapped[int] = mapped_column(default=0, comment="眷屬數量 0~N")
    pension_self_6: Mapped[bool] = mapped_column(Boolean, default=False, comment="員工自提6%（試算/結算時帶入 pension_self_6）")
    # 領薪方式與銀行資訊（內部系統：一律顯示完整，不做遮罩）
    pay_method: Mapped[str] = mapped_column(String(20), default="CASH", comment="領薪方式：SECURITY_FIRST/APARTMENT_FIRST/SMITH_FIRST/CASH/OTHER_BANK")
    bank_code: Mapped[Optional[str]] = mapped_column(String(20), comment="銀行代碼（3 碼）")
    branch_code: Mapped[Optional[str]] = mapped_column(String(20), comment="分行代碼（4 碼）")
    bank_account: Mapped[Optional[str]] = mapped_column(String(30), comment="銀行帳號（6～20 碼）")
    property_pay_mode: Mapped[Optional[str]] = mapped_column(String(30), comment="物業計薪模式：monthly/hourly/daily（相容舊值 WEEKLY_2H/MONTHLY_8H_HOLIDAY）")
    security_pay_mode: Mapped[Optional[str]] = mapped_column(String(20), comment="保全計薪模式：monthly/hourly/daily")
    smith_pay_mode: Mapped[Optional[str]] = mapped_column(String(20), comment="史密斯計薪模式：monthly/hourly/daily")
    lixiang_pay_mode: Mapped[Optional[str]] = mapped_column(String(20), comment="立翔人力計薪模式：monthly/hourly/daily")
    weekly_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="物業每週完成給付金額（僅 WEEKLY_2H 使用）")
    property_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="物業固定月薪（僅 payroll_type=property 使用）")
    registration_type: Mapped[str] = mapped_column(String(20), default="security", comment="登載身份：security=保全、property=物業、smith=史密斯、lixiang=立翔人力")
    safety_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), comment="安全查核 PDF 路徑")
    contract_84_1_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), comment="84-1 PDF 路徑")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dependents: Mapped[List["Dependent"]] = relationship("Dependent", back_populates="employee", cascade="all, delete-orphan")
    documents: Mapped[List["EmployeeDocument"]] = relationship("EmployeeDocument", back_populates="employee", cascade="all, delete-orphan")
    salary_profile: Mapped[Optional["SalaryProfile"]] = relationship("SalaryProfile", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    insurance_monthly_results: Mapped[List["InsuranceMonthlyResult"]] = relationship("InsuranceMonthlyResult", back_populates="employee", cascade="all, delete-orphan")
    site_assignments: Mapped[List["SiteEmployeeAssignment"]] = relationship("SiteEmployeeAssignment", back_populates="employee", cascade="all, delete-orphan")
    schedule_assignments: Mapped[List["ScheduleAssignment"]] = relationship("ScheduleAssignment", back_populates="employee", cascade="all, delete-orphan")


class Dependent(Base):
    """眷屬資料（一員工多眷屬）"""
    __tablename__ = "dependents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="dependent_id")
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50), comment="姓名")
    birth_date: Mapped[Optional[date]] = mapped_column(Date, comment="出生年月日")
    national_id: Mapped[Optional[str]] = mapped_column(String(500), comment="身分證字號（遮罩）")
    relation: Mapped[str] = mapped_column(String(20), comment="配偶/子女/父母/祖父母/其他")
    city: Mapped[Optional[str]] = mapped_column(String(30), comment="居住縣市：桃園市/台北市/其他")
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否身障")
    disability_level: Mapped[Optional[str]] = mapped_column(String(20), comment="輕度/中度/重度/極重度")
    notes: Mapped[Optional[str]] = mapped_column(String(200), comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="dependents")


class EmployeeDocument(Base):
    """員工檔案：安全查核 PDF、84-1 PDF（存路徑/檔名/上傳時間）"""
    __tablename__ = "employee_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(30), comment="safety_check / 84_1")
    file_name: Mapped[str] = mapped_column(String(255), comment="原始檔名")
    file_path: Mapped[str] = mapped_column(String(500), comment="儲存路徑")
    file_size: Mapped[Optional[int]] = mapped_column(comment="檔案大小 bytes")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="documents")


class InsuranceConfig(Base):
    """保險/勞退計算規則（可配置）"""
    __tablename__ = "insurance_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="設定鍵")
    config_value: Mapped[str] = mapped_column(Text, comment="JSON 或數值")
    description: Mapped[Optional[str]] = mapped_column(String(200), comment="說明")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RateTable(Base):
    """費率/級距表主檔：依類型、版本、生效區間"""
    __tablename__ = "rate_tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(40), index=True, comment="labor_insurance / health_insurance / occupational_accident / labor_pension")
    version: Mapped[str] = mapped_column(String(30), comment="版本代碼，如 2025-01")
    effective_from: Mapped[date] = mapped_column(Date, comment="生效起日（含）")
    effective_to: Mapped[Optional[date]] = mapped_column(Date, comment="生效訖日（含），空表持續有效")
    total_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), comment="總費率（如勞保 0.115）；空則由 items 之比例推算")
    note: Mapped[Optional[str]] = mapped_column(String(500), comment="備註")

    items: Mapped[List["RateItem"]] = relationship("RateItem", back_populates="table", cascade="all, delete-orphan", order_by="RateItem.salary_min")


class RateItem(Base):
    """費率/級距明細：薪資區間與負擔比例"""
    __tablename__ = "rate_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("rate_tables.id", ondelete="CASCADE"), index=True)
    level_name: Mapped[Optional[str]] = mapped_column(String(30), comment="級距名稱，如 26400")
    salary_min: Mapped[Decimal] = mapped_column(Numeric(12, 0), comment="薪資下限（含）")
    salary_max: Mapped[Decimal] = mapped_column(Numeric(12, 0), comment="薪資上限（含）")
    insured_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 0), comment="投保薪資級距（勞保用；空則以 salary_max 計）")
    employee_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, comment="個人負擔比例")
    employer_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, comment="公司負擔比例")
    gov_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), comment="政府負擔比例")
    fixed_amount_if_any: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="固定金額（若有）")

    table: Mapped["RateTable"] = relationship("RateTable", back_populates="items")


class InsuranceBracketImport(Base):
    """勞健保級距表匯入主檔（權威資料：上傳 Excel 後僅依此表查表計費）"""
    __tablename__ = "insurance_bracket_imports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), comment="原始檔名")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), comment="原檔儲存路徑，供下載備查")
    row_count: Mapped[int] = mapped_column(Integer, default=0, comment="匯入筆數（級距列數）")
    version: Mapped[Optional[str]] = mapped_column(String(60), comment="版本或備註")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brackets: Mapped[List["InsuranceBracket"]] = relationship(
        "InsuranceBracket", back_populates="import_record", cascade="all, delete-orphan", order_by="InsuranceBracket.insured_salary_level"
    )


class InsuranceBracket(Base):
    """級距表明細：每一級距對應之各項金額（公司/員工），查表後直接加總、不計率"""
    __tablename__ = "insurance_brackets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("insurance_bracket_imports.id", ondelete="CASCADE"), index=True)
    insured_salary_level: Mapped[int] = mapped_column(Integer, comment="投保薪資級距（整數，如 26400、42000）")
    labor_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="勞保公司負擔")
    labor_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="勞保員工負擔")
    health_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="健保公司負擔")
    health_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="健保員工負擔")
    occupational_accident: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="職災（全雇主）")
    labor_pension: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="勞退6%（全雇主）")
    group_insurance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="團保（全雇主，可選）")

    import_record: Mapped["InsuranceBracketImport"] = relationship("InsuranceBracketImport", back_populates="brackets")


class SalaryProfile(Base):
    """薪資設定（可擴充：排班/出勤影響薪資時使用）。
    月薪/日薪/時薪、是否計加班、計算規則。一員工一筆。"""
    __tablename__ = "salary_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True)
    salary_type: Mapped[str] = mapped_column(String(20), comment="月薪/日薪/時薪")
    monthly_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="月薪基數")
    daily_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="日薪單價")
    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="時薪單價")
    overtime_eligible: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否計加班")
    calculation_rules: Mapped[Optional[str]] = mapped_column(Text, comment="計算規則 JSON 或說明")
    group_insurance_enabled: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否扣團保")
    group_insurance_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="團保扣款金額，預設350")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="salary_profile")


class InsuranceMonthlyResult(Base):
    """保險費用計算結果落表，供會計抓 company cost。
    employee_id, year_month, item_type, employee_amount, employer_amount, gov_amount。"""
    __tablename__ = "insurance_monthly_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    year_month: Mapped[int] = mapped_column(Integer, index=True, comment="西元年月，如 202501")
    item_type: Mapped[str] = mapped_column(String(40), index=True, comment="labor_insurance / health_insurance / occupational_accident / labor_pension / group_insurance")
    employee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="個人負擔")
    employer_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="公司負擔")
    gov_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="政府負擔")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="insurance_monthly_results")


class Site(Base):
    """案場基本資料與人力/成本設定。後續排班與薪資可依案場計算成本與利潤。擴充：案場類型、服務類型、費用稅額、發票收款期限、客戶與發票資訊、到期提醒。"""
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True, comment="案場名稱")
    address: Mapped[str] = mapped_column(String(500), comment="案場地址")
    site_type: Mapped[Optional[str]] = mapped_column(String(20), index=True, comment="community/factory")
    service_types: Mapped[Optional[str]] = mapped_column(Text, comment="JSON 多選：駐衛保全/公寓大廈管理/保全綜合")
    contract_start: Mapped[date] = mapped_column(Date, comment="合約起始日")
    contract_end: Mapped[Optional[date]] = mapped_column(Date, index=True, comment="合約結束日")
    monthly_fee_excl_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="月服務費未稅")
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), comment="稅率 如 0.05")
    monthly_fee_incl_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="月服務費含稅")
    invoice_due_day: Mapped[Optional[int]] = mapped_column(Integer, comment="每月發票期限日 1-31")
    payment_due_day: Mapped[Optional[int]] = mapped_column(Integer, comment="每月收款期限日 1-31")
    remind_days: Mapped[Optional[int]] = mapped_column(Integer, comment="契約到期提醒天數 預設30")
    customer_name: Mapped[Optional[str]] = mapped_column(String(100), index=True, comment="客戶名稱")
    customer_tax_id: Mapped[Optional[str]] = mapped_column(String(20), comment="統一編號")
    customer_contact: Mapped[Optional[str]] = mapped_column(String(50), comment="聯絡人")
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), comment="電話")
    customer_email: Mapped[Optional[str]] = mapped_column(String(100), comment="Email")
    invoice_title: Mapped[Optional[str]] = mapped_column(String(200), comment="發票抬頭")
    invoice_mail_address: Mapped[Optional[str]] = mapped_column(String(500), comment="發票郵寄地址")
    invoice_receiver: Mapped[Optional[str]] = mapped_column(String(100), comment="收件人")
    # 既有欄位（排班/指派相容）
    client_name: Mapped[str] = mapped_column(String(100), index=True, comment="客戶名稱")
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="每月合約金額")
    payment_method: Mapped[str] = mapped_column(String(20), index=True, comment="收款方式")
    receivable_day: Mapped[int] = mapped_column(Integer, comment="每月應收日 1-31")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="備註")
    daily_required_count: Mapped[Optional[int]] = mapped_column(Integer, comment="每日需要人數")
    shift_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), comment="每班別工時")
    is_84_1: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否屬於 84-1 案場")
    night_shift_allowance: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="夜班加給金額")
    bear_labor_insurance: Mapped[bool] = mapped_column(Boolean, default=True, comment="此案場是否需負擔勞保公司負擔")
    bear_health_insurance: Mapped[bool] = mapped_column(Boolean, default=True, comment="此案場是否需負擔健保公司負擔")
    has_group_or_occupational: Mapped[bool] = mapped_column(Boolean, default=False, comment="此案場是否有團保或職災保費")
    rebate_type: Mapped[Optional[str]] = mapped_column(String(20), comment="案場回饋：amount/percent")
    rebate_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="回饋金額或百分比數值")
    # 軟刪除：移除案場僅標記，不實體刪除
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否有效（false=已移除或已歸檔）")
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="移除時間")
    deactivated_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="移除原因，如 manual")
    # 歷史案場：到期未續約自動歸檔（手動移除不設 is_archived）
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="是否為歷史案場（到期未續約）")
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="歸檔時間")
    archived_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="歸檔原因，如 expired_no_renew")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments: Mapped[List["SiteEmployeeAssignment"]] = relationship(
        "SiteEmployeeAssignment", back_populates="site", cascade="all, delete-orphan"
    )
    schedules: Mapped[List["Schedule"]] = relationship(
        "Schedule", back_populates="site", cascade="all, delete-orphan"
    )
    contract_files: Mapped[List["SiteContractFile"]] = relationship(
        "SiteContractFile", back_populates="site", cascade="all, delete-orphan"
    )
    rebates: Mapped[List["SiteRebate"]] = relationship(
        "SiteRebate", back_populates="site", cascade="all, delete-orphan"
    )
    monthly_receipts: Mapped[List["SiteMonthlyReceipt"]] = relationship(
        "SiteMonthlyReceipt", back_populates="site", cascade="all, delete-orphan"
    )


class SiteContractFile(Base):
    """案場合約附件 PDF"""
    __tablename__ = "site_contract_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255), comment="原始檔名")
    file_path: Mapped[str] = mapped_column(String(500), comment="儲存路徑")
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    site: Mapped["Site"] = relationship("Site", back_populates="contract_files")


class SiteRebate(Base):
    """案場回饋項目（多筆）"""
    __tablename__ = "site_rebates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    item_name: Mapped[str] = mapped_column(String(200), comment="回饋項目名稱")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已回饋")
    completed_date: Mapped[Optional[date]] = mapped_column(Date, comment="回饋日期")
    cost_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="公司花費金額")
    receipt_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), comment="回饋憑證 PDF 路徑")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site: Mapped["Site"] = relationship("Site", back_populates="rebates")


class SiteMonthlyReceipt(Base):
    """案場每月入帳登記（site_id + billing_month 唯一）"""
    __tablename__ = "site_monthly_receipts"
    __table_args__ = (UniqueConstraint("site_id", "billing_month", name="uq_site_billing_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    billing_month: Mapped[str] = mapped_column(String(7), index=True, comment="YYYY-MM")
    expected_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="本月應收金額")
    is_received: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已入帳")
    received_date: Mapped[Optional[date]] = mapped_column(Date, comment="入帳日期")
    received_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), comment="實際入帳金額")
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), comment="transfer/cash/check/other")
    proof_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), comment="匯款證明 PDF 路徑")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site: Mapped["Site"] = relationship("Site", back_populates="monthly_receipts")


class SiteEmployeeAssignment(Base):
    """案場-員工指派（多對多）。後續排班與薪資可依此計算案場成本與利潤。"""
    __tablename__ = "site_employee_assignments"
    __table_args__ = (UniqueConstraint("site_id", "employee_id", name="uq_site_employee"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, index=True, comment="指派生效日（可空表立即生效）")
    effective_to: Mapped[Optional[date]] = mapped_column(Date, index=True, comment="指派迄日（可空表持續）")
    notes: Mapped[Optional[str]] = mapped_column(String(200), comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    site: Mapped["Site"] = relationship("Site", back_populates="assignments")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="site_assignments")


# ---------- 排班 P0：schedules / schedule_shifts / schedule_assignments ----------
SCHEDULE_STATUSES = ("draft", "published", "locked")
SHIFT_CODES = ("day", "night", "reserved")  # 日 / 夜 / 保留
ASSIGNMENT_ROLES = ("leader", "post", "normal")  # 隊長 / 哨點 / 一般


class Schedule(Base):
    """排班表頭：某案場某年某月。"""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer, comment="年度")
    month: Mapped[int] = mapped_column(Integer, comment="月份 1-12")
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="draft / published / locked")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    site: Mapped["Site"] = relationship("Site", back_populates="schedules")
    shifts: Mapped[List["ScheduleShift"]] = relationship(
        "ScheduleShift", back_populates="schedule", cascade="all, delete-orphan", order_by="ScheduleShift.date, ScheduleShift.id"
    )


class ScheduleShift(Base):
    """排班明細：某日某班別。"""
    __tablename__ = "schedule_shifts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, comment="班別日期")
    shift_code: Mapped[str] = mapped_column(String(20), comment="日 day / 夜 night / 保留 reserved")
    start_time: Mapped[Optional[time]] = mapped_column(Time, comment="開始時間")
    end_time: Mapped[Optional[time]] = mapped_column(Time, comment="結束時間")
    required_headcount: Mapped[int] = mapped_column(Integer, default=1, comment="需求人數")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="shifts")
    assignments: Mapped[List["ScheduleAssignment"]] = relationship(
        "ScheduleAssignment", back_populates="shift", cascade="all, delete-orphan"
    )


class ScheduleAssignment(Base):
    """人員指派到班：某 shift 某員工、角色、是否確認。"""
    __tablename__ = "schedule_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("schedule_shifts.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="normal", comment="隊長 leader / 哨點 post / 一般 normal")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否確認")
    notes: Mapped[Optional[str]] = mapped_column(String(200), comment="備註")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    shift: Mapped["ScheduleShift"] = relationship("ScheduleShift", back_populates="assignments")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="schedule_assignments")


class AccountingPayrollResult(Base):
    """傻瓜會計薪資計算結果（依年/月/類型儲存，供查詢某年某月薪資）。"""
    __tablename__ = "accounting_payroll_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, index=True, comment="西元年")
    month: Mapped[int] = mapped_column(Integer, index=True, comment="1～12")
    type: Mapped[str] = mapped_column(String(30), index=True, comment="security / property / smith / cleaning")
    site: Mapped[str] = mapped_column(String(100), comment="案場名稱")
    employee: Mapped[str] = mapped_column(String(50), comment="員工姓名")
    pay_type: Mapped[Optional[str]] = mapped_column(String(20), comment="monthly/daily/hourly")
    total_hours: Mapped[float] = mapped_column(nullable=False, comment="總工時")
    gross_salary: Mapped[Optional[float]] = mapped_column(comment="應發")
    labor_insurance_employee: Mapped[Optional[float]] = mapped_column(comment="勞保自付")
    health_insurance_employee: Mapped[Optional[float]] = mapped_column(comment="健保自付")
    group_insurance: Mapped[Optional[float]] = mapped_column(comment="團保")
    self_pension_6: Mapped[Optional[float]] = mapped_column(comment="自提6%")
    deductions_total: Mapped[Optional[float]] = mapped_column(comment="扣款合計")
    net_salary: Mapped[Optional[float]] = mapped_column(comment="實發")
    total_salary: Mapped[float] = mapped_column(nullable=False, comment="總薪資(相容舊欄位，等同net_salary)")
    status: Mapped[str] = mapped_column(String(30), comment="滿班/未滿班/日薪制/時薪制/案場未建檔")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PatrolBindingCode(Base):
    """手機設備綁定碼（一次性，具有效期）。"""
    __tablename__ = "patrol_binding_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True, comment="綁定碼")
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, comment="到期時間")
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="使用時間（一次性）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PatrolDevice(Base):
    """已綁定巡邏設備。"""
    __tablename__ = "patrol_devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    binding_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patrol_binding_codes.id", ondelete="SET NULL"), nullable=True, index=True)
    device_public_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, comment="裝置永久識別碼 UUID")
    device_token: Mapped[str] = mapped_column(String(140), unique=True, index=True, comment="伺服器簽發設備 token")
    employee_name: Mapped[str] = mapped_column(String(80), index=True, comment="員工姓名")
    site_name: Mapped[str] = mapped_column(String(120), index=True, comment="案場名稱")
    device_fingerprint: Mapped[Optional[str]] = mapped_column(Text, comment="前端回傳設備指紋 JSON")
    user_agent: Mapped[Optional[str]] = mapped_column(String(600), comment="UA")
    platform: Mapped[Optional[str]] = mapped_column(String(120), comment="平台")
    browser: Mapped[Optional[str]] = mapped_column(String(120), comment="瀏覽器")
    language: Mapped[Optional[str]] = mapped_column(String(30), comment="語言")
    screen_size: Mapped[Optional[str]] = mapped_column(String(40), comment="螢幕尺寸")
    timezone: Mapped[Optional[str]] = mapped_column(String(80), comment="時區")
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), comment="來源 IP")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), comment="綁定密碼雜湊值")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否仍為有效綁定")
    bound_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    unbound_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="解除綁定時間")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    logs: Mapped[List["PatrolLog"]] = relationship("PatrolLog", back_populates="device", cascade="all, delete-orphan")


class PatrolDeviceBinding(Base):
    """永久裝置綁定主檔（商用入口）。"""
    __tablename__ = "patrol_device_bindings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, comment="裝置永久識別碼 UUID")
    employee_name: Mapped[Optional[str]] = mapped_column(String(80), index=True, comment="員工姓名")
    site_name: Mapped[Optional[str]] = mapped_column(String(120), index=True, comment="案場名稱")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), comment="綁定密碼雜湊值")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否仍為有效綁定")
    bound_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True, comment="綁定時間")
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True, comment="最後登入/使用時間")
    device_info: Mapped[Optional[dict]] = mapped_column(JSON, comment="設備資訊 JSON（ua/platform/lang/screen/tz）")
    user_agent: Mapped[Optional[str]] = mapped_column(String(600), comment="UA")
    platform: Mapped[Optional[str]] = mapped_column(String(120), comment="平台")
    browser: Mapped[Optional[str]] = mapped_column(String(120), comment="瀏覽器")
    language: Mapped[Optional[str]] = mapped_column(String(30), comment="語言")
    screen_size: Mapped[Optional[str]] = mapped_column(String(40), comment="螢幕尺寸")
    timezone: Mapped[Optional[str]] = mapped_column(String(80), comment="時區")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PatrolPoint(Base):
    """巡邏點設定。"""
    __tablename__ = "patrol_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, comment="對外公開固定 UUID")
    point_code: Mapped[str] = mapped_column(String(80), unique=True, index=True, comment="巡邏點編號")
    point_name: Mapped[str] = mapped_column(String(120), comment="巡邏點名稱")
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    site_name: Mapped[Optional[str]] = mapped_column(String(120), index=True, comment="案場名稱（快照）")
    location: Mapped[Optional[str]] = mapped_column(String(255), comment="巡邏點位置說明")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="巡邏點是否啟用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs: Mapped[List["PatrolLog"]] = relationship("PatrolLog", back_populates="point", cascade="all, delete-orphan")


class PatrolLog(Base):
    """巡邏打點紀錄。"""
    __tablename__ = "patrol_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patrol_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    point_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patrol_points.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_name: Mapped[str] = mapped_column(String(80), index=True)
    site_name: Mapped[str] = mapped_column(String(120), index=True)
    point_code: Mapped[str] = mapped_column(String(80), index=True)
    point_name: Mapped[str] = mapped_column(String(120))
    checkin_date: Mapped[date] = mapped_column(Date, index=True)
    checkin_time: Mapped[time] = mapped_column(Time)
    checkin_ampm: Mapped[str] = mapped_column(String(10), comment="上午/下午")
    qr_value: Mapped[Optional[str]] = mapped_column(String(1000), comment="原始 QR 字串")
    device_info: Mapped[Optional[str]] = mapped_column(Text, comment="設備資訊快照 JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    device: Mapped[Optional["PatrolDevice"]] = relationship("PatrolDevice", back_populates="logs")
    point: Mapped[Optional["PatrolPoint"]] = relationship("PatrolPoint", back_populates="logs")
