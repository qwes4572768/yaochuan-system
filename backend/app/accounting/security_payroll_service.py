"""
傻瓜會計 - 保全核心計算（升級版）。
解析保全時數檔案（多 sheet = 多案場）→ 每人每日工時 → 每月工時 → 薪資計算（月/日/時薪）→ 扣款（勞健保/團保/自提6%）。
團保依加保日期(enroll_date)按 30 天/月、per_day=月費/30 計算當月天數。
"""
import calendar
import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional, Any, Dict
from collections import defaultdict
import io

logger = logging.getLogger(__name__)

PROPERTY_PAY_MODES = {"WEEKLY_2H", "MONTHLY_8H_HOLIDAY"}
EMPLOYEE_REGISTRATION_TYPES = {"security", "property", "smith", "lixiang", "cleaning"}
COMPANY_PAY_MODES = {"monthly", "daily", "hourly"}

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    get_employee_by_name_with_registration_priority,
    get_site_by_name,
    get_latest_bracket_import,
    get_bracket_by_level,
)
from app.accounting.holiday_calendar import get_holiday_dates


# 一列一筆格式：必要欄位與可接受之表頭別名（小寫比對）
COLUMN_ALIASES = {
    "site_name": ["site_name", "site", "案場", "案場名稱"],
    "employee_name": ["employee_name", "employee", "員工", "員工姓名", "姓名"],
    "date": ["date", "日期"],
    "hours": ["hours", "工時"],
}


def _normalize_columns(df: pd.DataFrame) -> Optional[dict]:
    """將 DataFrame 欄位對應到 site_name, employee_name, date, hours。缺一則回傳 None。"""
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    mapping = {}
    for key, aliases in COLUMN_ALIASES.items():
        found = None
        for a in aliases:
            if a.lower() in cols_lower:
                found = cols_lower[a.lower()]
                break
        if found is None:
            return None
        mapping[key] = found
    return mapping


def _parse_one_row_format(df: pd.DataFrame) -> Optional[List[dict]]:
    """嘗試解析一列一筆格式。若表頭不符或無資料列則回傳 None。"""
    mapping = _normalize_columns(df)
    if not mapping:
        return None
    rows = []
    for _, r in df.iterrows():
        site_val = r.get(mapping["site_name"])
        emp_val = r.get(mapping["employee_name"])
        date_val = r.get(mapping["date"])
        hours_val = r.get(mapping["hours"])
        if pd.isna(site_val) and pd.isna(emp_val) and pd.isna(date_val) and pd.isna(hours_val):
            continue
        site = str(site_val).strip() if not pd.isna(site_val) else ""
        employee = str(emp_val).strip() if not pd.isna(emp_val) else ""
        if pd.isna(date_val):
            continue
        if isinstance(date_val, datetime):
            dt = date_val
        elif isinstance(date_val, pd.Timestamp):
            dt = date_val.to_pydatetime()
        else:
            try:
                dt = pd.to_datetime(date_val).to_pydatetime()
            except Exception:
                continue
        try:
            h = float(hours_val) if not pd.isna(hours_val) else 0.0
        except (TypeError, ValueError):
            h = 0.0
        rows.append({"site": site, "employee": employee, "date": dt, "hours": h})
    return rows if rows else None


def _cell_str(val: Any) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    return s


def _cell_float(val: Any) -> float:
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _is_twodigit_label(val: Any) -> bool:
    """第1欄是否為兩位數標籤（如 01、02）用於案場。"""
    s = _cell_str(val)
    if len(s) != 2:
        return False
    return s.isdigit()


def _site_from_sheet_name(sheet_name: str) -> Optional[str]:
    """從 sheet 名稱去掉前綴編號取得案場名，例如 01_西雅圖 -> 西雅圖。"""
    s = (sheet_name or "").strip()
    if not s:
        return None
    m = re.match(r"^\d+_?\s*(.*)$", s)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def _parse_calendar_matrix_one_sheet(
    df_raw: pd.DataFrame,
    year: int,
    month: int,
    sheet_name: Optional[str] = None,
    site_override: Optional[str] = None,
) -> Tuple[List[dict], List[str]]:
    """
    解析單一 sheet 月曆矩陣型。使用 UI 的 year, month 組 date。
    回傳 (records, sheet_errors)。錯誤訊息可帶 sheet【名稱】前綴。
    """
    err_prefix = f"sheet【{sheet_name}】" if sheet_name else ""
    errors: List[str] = []
    if df_raw is None or df_raw.empty or len(df_raw) < 3:
        errors.append(f"{err_prefix}找不到表頭：類別/姓名/日期/1..31")
        return [], errors

    ncols = df_raw.shape[1]
    header_row_idx: Optional[int] = None
    day_columns: dict[int, int] = {}

    for i in range(len(df_raw)):
        row = df_raw.iloc[i]
        if ncols < 3:
            continue
        c0, c1, c2 = _cell_str(row.iloc[0]), _cell_str(row.iloc[1]), _cell_str(row.iloc[2])
        if c0 != "類別" or c1 != "姓名" or c2 != "日期":
            continue
        day_columns = {}
        for j in range(3, min(ncols, 3 + 35)):
            try:
                v = row.iloc[j]
                if pd.isna(v):
                    continue
                d = int(float(v)) if isinstance(v, (int, float)) else int(str(v).strip())
                if 1 <= d <= 31:
                    day_columns[d] = j
            except (ValueError, TypeError):
                continue
        if len(day_columns) < 1:
            errors.append(f"{err_prefix}找不到日期欄位（1~31）")
            return [], errors
        header_row_idx = i
        break

    if header_row_idx is None:
        errors.append(f"{err_prefix}找不到表頭：類別/姓名/日期/1..31")
        return [], errors

    # 案場名稱：優先用 site_override（來自 sheet 名），否則表格內第2列
    site_name = site_override or "未填案場"
    if not site_override:
        for r in range(header_row_idx - 1, -1, -1):
            row = df_raw.iloc[r]
            if ncols < 2:
                continue
            if _is_twodigit_label(row.iloc[0]) and _cell_str(row.iloc[1]):
                site_name = _cell_str(row.iloc[1])
                break

    data_start = header_row_idx + 2
    if data_start >= len(df_raw):
        errors.append(f"{err_prefix}找不到任何員工（日/夜）資料列")
        return [], errors

    df_data = df_raw.iloc[data_start:].copy()
    if df_data.empty:
        errors.append(f"{err_prefix}找不到任何員工（日/夜）資料列")
        return [], errors

    df_data.iloc[:, 0] = df_data.iloc[:, 0].ffill()
    df_data.iloc[:, 1] = df_data.iloc[:, 1].ffill()
    col2 = df_data.iloc[:, 2].astype(str).str.strip()
    df_data = df_data[col2.isin(["日", "夜"])].copy()
    if df_data.empty:
        errors.append(f"{err_prefix}找不到任何員工（日/夜）資料列")
        return [], errors

    employee_rows: dict[str, List[Tuple[str, pd.Series]]] = defaultdict(list)
    for _, row in df_data.iterrows():
        name = _cell_str(row.iloc[1])
        shift = _cell_str(row.iloc[2])
        if not name:
            continue
        employee_rows[name].append((shift, row))

    _, last_day = calendar.monthrange(year, month)
    out: List[dict] = []
    for employee, shift_rows in employee_rows.items():
        for day in range(1, last_day + 1):
            col_idx = day_columns.get(day)
            if col_idx is None:
                continue
            hours = 0.0
            for shift, row in shift_rows:
                hours += _cell_float(row.iloc[col_idx])
            try:
                dt = datetime(year, month, day)
            except ValueError:
                continue
            out.append({"site": site_name, "employee": employee, "date": dt, "hours": hours})
    return out, []


def parse_security_hours_file(
    content: bytes,
    filename: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Tuple[List[dict], List[str]]:
    """
    解析保全時數檔。當有 year, month 時優先嘗試多 sheet 月曆矩陣型；否則單 sheet 一列一筆或月曆。
    回傳 (records, parse_errors)。records = [ {"site", "employee", "date", "hours"}, ... ]
    """
    ext = (filename or "").lower().split(".")[-1]
    if ext not in ("xlsx", "xls", "ods"):
        raise ValueError("不支援的檔案格式，僅支援 xlsx / xls / ods")

    parse_errors: List[str] = []

    # 多 sheet 月曆矩陣型（xlsx / ods；xls 多 sheet 依引擎而定）
    if year is not None and month is not None and ext in ("xlsx", "ods"):
        buf = io.BytesIO(content)
        try:
            if ext == "ods":
                all_sheets = pd.read_excel(buf, engine="odf", sheet_name=None, header=None)
            else:
                all_sheets = pd.read_excel(buf, engine="openpyxl", sheet_name=None, header=None)
        except Exception:
            all_sheets = {}
        if isinstance(all_sheets, dict) and all_sheets:
            all_records: List[dict] = []
            for sh_name, df_raw in all_sheets.items():
                if df_raw is None or df_raw.empty:
                    continue
                site_from_sheet = _site_from_sheet_name(sh_name)
                recs, errs = _parse_calendar_matrix_one_sheet(
                    df_raw, year, month, sheet_name=sh_name, site_override=site_from_sheet
                )
                parse_errors.extend(errs)
                all_records.extend(recs)
            if all_records:
                return (all_records, parse_errors)
            if parse_errors:
                raise ValueError("檔案格式不支援：找不到表頭（類別/姓名/日期）或日期欄位（1~31）")
            raise ValueError("檔案沒有任何可解析的 sheet")
        elif isinstance(all_sheets, dict) and not all_sheets:
            raise ValueError("檔案沒有任何可解析的 sheet")

    # 單 sheet：一列一筆 或 月曆矩陣
    def read_with_header(hdr: Optional[int] = 0, sheet: int = 0) -> pd.DataFrame:
        buf = io.BytesIO(content)
        if ext == "ods":
            return pd.read_excel(buf, engine="odf", sheet_name=sheet, header=hdr)
        if ext == "xls":
            return pd.read_excel(buf, engine="xlrd", sheet_name=sheet, header=hdr)
        return pd.read_excel(buf, engine="openpyxl", sheet_name=sheet, header=hdr)

    df = read_with_header(0)
    if df is not None and not df.empty:
        one_row = _parse_one_row_format(df)
        if one_row is not None and len(one_row) > 0:
            return (one_row, [])

    if year is None or month is None:
        raise ValueError("檔案格式不支援：找不到表頭（類別/姓名/日期）或日期欄位（1~31）")
    df_raw = read_with_header(None)
    if df_raw is None or df_raw.empty:
        raise ValueError("檔案格式不支援：找不到表頭（類別/姓名/日期）或日期欄位（1~31）")
    recs, errs = _parse_calendar_matrix_one_sheet(df_raw, year, month)
    if recs:
        return (recs, errs)
    if errs:
        raise ValueError(errs[0] if errs else "檔案格式不支援：找不到表頭（類別/姓名/日期）或日期欄位（1~31）")
    raise ValueError("檔案格式不支援：找不到表頭（類別/姓名/日期）或日期欄位（1~31）")


def _get_pay_info(employee: Any) -> Optional[dict]:
    """
    從員工 + salary_profile 取得薪資制度與金額。
    回傳 dict: pay_type('monthly'|'daily'|'hourly'), monthly_salary, daily_wage, hourly_wage,
               insured_salary_level, group_insurance_enabled, group_insurance_fee, pension_self_6。
    缺必要欄位時回傳 None。
    """
    st = getattr(employee, "salary_type", None) or ""
    st = (st or "").strip()
    profile = getattr(employee, "salary_profile", None)
    monthly = None
    daily = None
    hourly = None
    if st == "月薪":
        v = getattr(employee, "salary_value", None)
        if v is not None:
            monthly = float(v)
        if monthly is None and profile and getattr(profile, "monthly_base", None) is not None:
            monthly = float(profile.monthly_base)
    elif st == "日薪":
        v = getattr(employee, "salary_value", None)
        if v is not None:
            daily = float(v)
        if daily is None and profile and getattr(profile, "daily_rate", None) is not None:
            daily = float(profile.daily_rate)
    elif st == "時薪":
        v = getattr(employee, "salary_value", None)
        if v is not None:
            hourly = float(v)
        if hourly is None and profile and getattr(profile, "hourly_rate", None) is not None:
            hourly = float(profile.hourly_rate)
    if not st or st not in ("月薪", "日薪", "時薪"):
        if profile:
            st = (getattr(profile, "salary_type", None) or "").strip()
            if st == "月薪" and getattr(profile, "monthly_base", None) is not None:
                monthly = float(profile.monthly_base)
            elif st == "日薪" and getattr(profile, "daily_rate", None) is not None:
                daily = float(profile.daily_rate)
            elif st == "時薪" and getattr(profile, "hourly_rate", None) is not None:
                hourly = float(profile.hourly_rate)
    pay_type = None
    if st == "月薪":
        pay_type = "monthly"
        if monthly is None or monthly <= 0:
            return None
        if daily is None:
            daily = round(monthly / 24, 0)
        if hourly is None:
            hourly = round(daily / 12, 0)
    elif st == "日薪":
        pay_type = "daily"
        if daily is None or daily <= 0:
            return None
        daily = round(daily, 0)
        if hourly is None:
            hourly = round(daily / 12, 0)
    elif st == "時薪":
        pay_type = "hourly"
        if hourly is None or hourly <= 0:
            return None
        hourly = round(hourly, 0)
    else:
        return None
    level = getattr(employee, "insured_salary_level", None)
    insured_level = int(level) if level is not None else None
    group_enabled = True
    group_fee = 0.0
    if profile:
        group_enabled = getattr(profile, "group_insurance_enabled", None)
        if group_enabled is None:
            group_enabled = True
        else:
            group_enabled = bool(group_enabled)
        gf = getattr(profile, "group_insurance_fee", None)
        if gf is not None and float(gf) > 0:
            group_fee = float(gf)
    if group_enabled and group_fee <= 0:
        group_fee = 350.0
    pension_self_6 = bool(getattr(employee, "pension_self_6", False))
    return {
        "pay_type": pay_type,
        "monthly_salary": int(round(monthly or 0, 0)),
        "daily_wage": int(round(daily or 0, 0)),
        "hourly_wage": int(round(hourly or 0, 0)),
        "insured_salary_level": insured_level,
        "group_insurance_enabled": group_enabled,
        "group_insurance_fee": group_fee,
        "pension_self_6": pension_self_6,
    }


def _calc_group_insurance(
    enroll_date: Optional[date],
    year: int,
    month: int,
    group_insurance_enabled: bool,
    group_insurance_fee: float,
) -> Tuple[float, int, float]:
    """
    團保依加保日期按 30 天/月計算。
    month_start = YYYY-MM-01, month_end = 當月第 30 天（固定 30 天）。
    回傳 (group_insurance, days, monthly_fee)。
    """
    if not group_insurance_enabled:
        return (0.0, 0, 0.0)
    monthly_fee = group_insurance_fee if group_insurance_fee > 0 else 350.0
    per_day = monthly_fee / 30.0
    month_start = date(year, month, 1)
    month_end = month_start + timedelta(days=29)
    if enroll_date is None:
        return (0.0, 0, monthly_fee)
    if enroll_date > month_end:
        return (0.0, 0, monthly_fee)
    if enroll_date <= month_start:
        days = 30
    else:
        days = (month_end - enroll_date).days + 1
    amount = int(round(per_day * days, 0))
    return (amount, days, monthly_fee)


def get_holiday_count(year: int, month: int) -> int:
    """計算指定月份假日天數（週六週日 + 國定假日）。"""
    return len(get_holiday_dates(year, month))


def _registration_type_label(registration_type: Optional[str]) -> str:
    return {
        "security": "保全",
        "property": "物業",
        "smith": "史密斯",
        "lixiang": "立翔人力",
        "cleaning": "清潔",
    }.get((registration_type or "").strip().lower(), "未知")


def _payroll_type_label(payroll_type: str) -> str:
    return {
        "security": "保全",
        "property": "物業",
        "smith": "史密斯",
        "lixiang": "立翔人力",
        "cleaning": "清潔",
    }.get((payroll_type or "").strip().lower(), "薪資")


def _current_pay_mode_raw(employee: Any, payroll_type: str) -> str:
    key = (payroll_type or "").strip().lower()
    if key == "property":
        return (getattr(employee, "property_pay_mode", None) or "").strip()
    if key == "security":
        return (getattr(employee, "security_pay_mode", None) or "").strip()
    if key == "smith":
        return (getattr(employee, "smith_pay_mode", None) or "").strip()
    if key == "lixiang":
        return (getattr(employee, "lixiang_pay_mode", None) or "").strip()
    return ""


def _build_pay_info_by_company_mode(employee: Any, mode: str) -> Optional[dict]:
    mode_key = (mode or "").strip().lower()
    if mode_key not in COMPANY_PAY_MODES:
        return None
    profile = getattr(employee, "salary_profile", None)
    salary_value = getattr(employee, "salary_value", None)
    monthly = None
    daily = None
    hourly = None
    if mode_key == "monthly":
        if salary_value is not None:
            monthly = float(salary_value)
        if monthly is None and profile and getattr(profile, "monthly_base", None) is not None:
            monthly = float(profile.monthly_base)
        if monthly is None or monthly <= 0:
            return None
        daily = round(monthly / 24, 0)
        hourly = round(daily / 12, 0)
    elif mode_key == "daily":
        if salary_value is not None:
            daily = float(salary_value)
        if daily is None and profile and getattr(profile, "daily_rate", None) is not None:
            daily = float(profile.daily_rate)
        if daily is None or daily <= 0:
            return None
        daily = round(daily, 0)
        hourly = round(daily / 12, 0)
    else:
        if salary_value is not None:
            hourly = float(salary_value)
        if hourly is None and profile and getattr(profile, "hourly_rate", None) is not None:
            hourly = float(profile.hourly_rate)
        if hourly is None or hourly <= 0:
            return None
        hourly = round(hourly, 0)

    level = getattr(employee, "insured_salary_level", None)
    insured_level = int(level) if level is not None else None
    group_enabled = True
    group_fee = 0.0
    if profile:
        group_enabled = getattr(profile, "group_insurance_enabled", None)
        if group_enabled is None:
            group_enabled = True
        else:
            group_enabled = bool(group_enabled)
        gf = getattr(profile, "group_insurance_fee", None)
        if gf is not None and float(gf) > 0:
            group_fee = float(gf)
    if group_enabled and group_fee <= 0:
        group_fee = 350.0
    pension_self_6 = bool(getattr(employee, "pension_self_6", False))
    return {
        "pay_type": mode_key,
        "monthly_salary": int(round(monthly or 0, 0)),
        "daily_wage": int(round(daily or 0, 0)),
        "hourly_wage": int(round(hourly or 0, 0)),
        "insured_salary_level": insured_level,
        "group_insurance_enabled": group_enabled,
        "group_insurance_fee": group_fee,
        "pension_self_6": pension_self_6,
    }


def _get_property_pay_info(employee: Any) -> Optional[dict]:
    mode_raw = getattr(employee, "property_pay_mode", None)
    property_pay_mode = (mode_raw or "").strip().upper()
    weekly_amount = getattr(employee, "weekly_amount", None)
    weekly_num = float(weekly_amount) if weekly_amount is not None else None
    property_salary = getattr(employee, "property_salary", None)
    salary_num = float(property_salary) if property_salary is not None else None
    return {
        "pay_type": "monthly",
        "property_pay_mode": property_pay_mode,
        "weekly_amount": weekly_num,
        "property_salary": salary_num,
        "insured_salary_level": int(getattr(employee, "insured_salary_level", 0) or 0) or None,
        "group_insurance_enabled": True,
        "group_insurance_fee": 350.0,
        "pension_self_6": bool(getattr(employee, "pension_self_6", False)),
    }


class SecurityPayrollCalculator:
    """
    保全薪資計算（升級版）：月/日/時薪制、勞健保/團保/自提6% 扣款。
    案場未建檔仍計算並標示 status=案場未建檔。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _property_weekly_required_weeks(self, year: int, month: int) -> int:
        _, last_day = calendar.monthrange(year, month)
        all_weeks = {
            (date(year, month, day).isocalendar().year, date(year, month, day).isocalendar().week)
            for day in range(1, last_day + 1)
        }
        return len(all_weeks)

    def _property_weekly_completed_weeks(self, daily_hours_by_date: Dict[date, float], year: int, month: int) -> int:
        weekly_totals: Dict[Tuple[int, int], float] = defaultdict(float)
        for d, hours in daily_hours_by_date.items():
            if d.year != year or d.month != month:
                continue
            week_key = (d.isocalendar().year, d.isocalendar().week)
            weekly_totals[week_key] += float(hours or 0)
        return sum(1 for total in weekly_totals.values() if total >= 2)

    def _build_property_weekly_result(
        self,
        employee_name: str,
        pay_info: dict,
        daily_hours_by_date: Dict[date, float],
        year: int,
        month: int,
    ) -> Tuple[int, str]:
        property_salary = pay_info.get("property_salary")
        if property_salary is None or property_salary <= 0:
            logger.warning(
                "property salary missing/invalid; set zero payroll. employee=%s year=%s month=%s",
                employee_name,
                year,
                month,
            )
            return 0, "未設定物業薪資"
        weekly_amount = pay_info.get("weekly_amount")
        if weekly_amount is None or weekly_amount <= 0:
            logger.warning(
                "weekly amount missing/invalid; set zero payroll. employee=%s year=%s month=%s",
                employee_name,
                year,
                month,
            )
            return 0, "未設定物業週薪"

        required_weeks = self._property_weekly_required_weeks(year, month)
        completed_weeks = self._property_weekly_completed_weeks(daily_hours_by_date, year, month)
        gross = int(round(float(weekly_amount) * completed_weeks, 0))
        gross = min(gross, int(round(float(property_salary), 0)))
        gross = max(gross, 0)
        return gross, f"每週2小時：完成 {completed_weeks}/{required_weeks} 週"

    def _build_property_weekly_site_distribution(
        self,
        employee_name: str,
        pay_info: dict,
        site_daily_hours: Dict[str, Dict[date, float]],
        year: int,
        month: int,
    ) -> Tuple[Dict[str, int], str]:
        property_salary = pay_info.get("property_salary")
        if property_salary is None or property_salary <= 0:
            logger.warning(
                "property salary missing/invalid; set zero payroll. employee=%s year=%s month=%s",
                employee_name,
                year,
                month,
            )
            return {}, "未設定物業薪資"
        weekly_amount = pay_info.get("weekly_amount")
        if weekly_amount is None or weekly_amount <= 0:
            logger.warning(
                "weekly amount missing/invalid; set zero payroll. employee=%s year=%s month=%s",
                employee_name,
                year,
                month,
            )
            return {}, "未設定物業週薪"

        required_weeks = self._property_weekly_required_weeks(year, month)
        weekly_amount_int = int(round(float(weekly_amount), 0))
        property_salary_int = int(round(float(property_salary), 0))

        weekly_totals: Dict[Tuple[int, int], float] = defaultdict(float)
        appeared_sites: set[str] = set()
        for site_name, day_map in (site_daily_hours or {}).items():
            for d, hours in (day_map or {}).items():
                if d.year != year or d.month != month:
                    continue
                appeared_sites.add(site_name)
                week_key = (d.isocalendar().year, d.isocalendar().week)
                weekly_totals[week_key] += float(hours or 0)

        completed_weeks = sum(1 for weekly_hours in weekly_totals.values() if weekly_hours >= 2)
        gross_total = min(property_salary_int, weekly_amount_int * completed_weeks)
        gross_total = max(gross_total, 0)

        sites = sorted(appeared_sites)
        if not sites:
            return {}, f"每週2小時：完成 {completed_weeks}/{required_weeks} 週"

        base = gross_total // len(sites)
        remainder = gross_total % len(sites)
        site_allocated: Dict[str, int] = {}
        for idx, site_name in enumerate(sites):
            site_allocated[site_name] = base + (1 if idx < remainder else 0)

        return site_allocated, f"每週2小時：完成 {completed_weeks}/{required_weeks} 週"

    def _build_property_monthly_result(
        self,
        employee_name: str,
        pay_info: dict,
        daily_hours_by_date: Dict[date, float],
        year: int,
        month: int,
    ) -> Tuple[int, str]:
        property_salary = pay_info.get("property_salary")
        if property_salary is None or property_salary <= 0:
            logger.warning(
                "property salary missing/invalid; set zero payroll. employee=%s year=%s month=%s",
                employee_name,
                year,
                month,
            )
            return 0, "未設定物業薪資"

        _, last_day = calendar.monthrange(year, month)
        holiday_dates = get_holiday_dates(year, month)
        required_work_days = max(last_day - len(holiday_dates), 0)
        if required_work_days <= 0:
            return 0, "出勤 0/0（按比例）"

        effective_days = sum(
            1 for d, day_hours in daily_hours_by_date.items()
            if d.year == year and d.month == month and float(day_hours or 0) >= 8
        )
        effective_days = min(effective_days, required_work_days)
        gross = int(round(float(property_salary) * (effective_days / required_work_days), 0))
        gross = min(gross, int(round(float(property_salary), 0)))
        gross = max(gross, 0)
        if effective_days >= required_work_days:
            return gross, f"滿班（{required_work_days}天）"
        return gross, f"出勤 {effective_days}/{required_work_days}（按比例）"

    def _build_property_result_for_employee(
        self,
        employee_name: str,
        pay_info: dict,
        daily_hours_by_date: Dict[date, float],
        year: int,
        month: int,
    ) -> Tuple[int, str]:
        mode = (pay_info.get("property_pay_mode") or "").strip().upper()
        if mode == "WEEKLY_2H":
            return self._build_property_weekly_result(employee_name, pay_info, daily_hours_by_date, year, month)
        if mode == "MONTHLY_8H_HOLIDAY":
            return self._build_property_monthly_result(employee_name, pay_info, daily_hours_by_date, year, month)
        logger.warning(
            "property mode missing/invalid; set zero payroll. employee=%s mode=%s",
            employee_name,
            mode,
        )
        return 0, "未設定物業模式"

    async def validate_and_calculate(
        self,
        rows: List[dict],
        year: int,
        month: int,
        payroll_type: str = "security",
        extra_payroll_types: Optional[List[str]] = None,
    ) -> Tuple[List[dict], List[Dict[str, Any]], Optional[dict]]:
        """
        驗證每筆、按 (site, employee) 彙總工時，依 pay_type 算 gross，再扣款得 net。
        回傳 (results, errors, debug)。debug 僅針對指定員工（游念棠）含每日 raw/rounded 與加總。
        """
        errors: List[Dict[str, Any]] = []
        valid_rows: List[dict] = []
        seen_employee_err: set = set()
        seen_site_err: set = set()
        seen_pay_err: set = set()
        seen_level_err: set = set()
        seen_bracket_err: set = set()
        seen_enroll_err: set = set()
        current_type = (payroll_type or "").strip().lower()
        dedup_extra_types: List[str] = []
        seen_extra_types: set[str] = set()
        for t in (extra_payroll_types or []):
            key = (t or "").strip().lower()
            if (
                not key
                or key == current_type
                or key in seen_extra_types
                or key not in EMPLOYEE_REGISTRATION_TYPES
            ):
                continue
            seen_extra_types.add(key)
            dedup_extra_types.append(key)

        for r in rows:
            site_name = (r.get("site") or "").strip()
            employee_name = (r.get("employee") or "").strip()
            dt = r.get("date")
            hours = r.get("hours", 0.0)
            try:
                hours = float(hours)
            except (TypeError, ValueError):
                hours = 0.0

            if hours < 0 or hours > 24:
                date_str = dt.strftime("%Y-%m-%d") if isinstance(dt, datetime) else str(dt)
                if hours > 24:
                    errors.append(
                        {
                            "type": "validation_error",
                            "message": f"員工【{employee_name}】{date_str} 工時異常（超過24小時）",
                        }
                    )
                else:
                    errors.append(
                        {
                            "type": "validation_error",
                            "message": f"員工【{employee_name}】{date_str} 工時異常（小於0）",
                        }
                    )
                continue

            employee = await get_employee_by_name_with_registration_priority(
                self.db,
                employee_name,
                current_registration_type=current_type,
                extra_registration_types=dedup_extra_types,
                load_salary_profile=True,
            )
            if not employee:
                if employee_name not in seen_employee_err:
                    seen_employee_err.add(employee_name)
                    errors.append(
                        {
                            "type": "employee_not_found",
                            "employee_name": employee_name,
                            "current_payroll_type": current_type,
                            "message": f"員工【{employee_name}】未建立",
                        }
                    )
                continue

            mode_raw = _current_pay_mode_raw(employee, current_type)
            mode_lower = mode_raw.lower()
            mode_upper = mode_raw.upper()
            source_type = (getattr(employee, "registration_type", None) or "").strip().lower()
            source_note = (
                f"（來源：{_registration_type_label(source_type)}）"
                if source_type and source_type != current_type
                else ""
            )
            if not mode_raw:
                if employee_name not in seen_pay_err:
                    seen_pay_err.add(employee_name)
                    errors.append(
                        {
                            "type": "missing_pay_config",
                            "employee_id": getattr(employee, "id", None),
                            "employee_name": employee_name,
                            "current_payroll_type": current_type,
                            "source_payroll_type": source_type or None,
                            "message": f"員工【{employee_name}】未設定{_payroll_type_label(current_type)}計薪模式{source_note}",
                        }
                    )
                continue

            if payroll_type == "property" and mode_upper in PROPERTY_PAY_MODES:
                pay_info = _get_property_pay_info(employee)
            elif mode_lower in COMPANY_PAY_MODES:
                pay_info = _build_pay_info_by_company_mode(employee, mode_lower)
            elif payroll_type != "property":
                pay_info = _get_pay_info(employee)
            else:
                pay_info = None
            if not pay_info:
                if employee_name not in seen_pay_err:
                    seen_pay_err.add(employee_name)
                    errors.append(
                        {
                            "type": "missing_pay_config",
                            "employee_id": getattr(employee, "id", None),
                            "employee_name": employee_name,
                            "current_payroll_type": current_type,
                            "source_payroll_type": source_type or None,
                            "message": f"員工【{employee_name}】未設定{_payroll_type_label(current_type)}計薪模式{source_note}",
                        }
                    )
                continue

            site = await get_site_by_name(self.db, site_name)
            if not site and site_name not in seen_site_err:
                seen_site_err.add(site_name)
                errors.append(
                    {
                        "type": "site_not_found",
                        "site_name": site_name,
                        "message": f"案場【{site_name}】未建立，請先到案場管理新增",
                    }
                )

            enroll_d = getattr(employee, "enroll_date", None)
            valid_rows.append({
                "site": site_name,
                "employee": employee_name,
                "date": dt,
                "hours": hours,
                "_pay_info": pay_info,
                "_enroll_date": enroll_d,
                "_employee_registration_type": (getattr(employee, "registration_type", None) or "").strip().lower(),
            })

        groups: dict[Tuple[str, str], dict] = defaultdict(
            lambda: {
                "hours_list": [],
                "daily_salaries": [],
                "pay_info": None,
                "enroll_date": None,
                "daily_hours_by_date": defaultdict(float),
                "employee_registration_type": "",
            }
        )
        DEBUG_EMPLOYEE = "游念棠"
        for r in valid_rows:
            key = (r["site"], r["employee"])
            employee_name = r["employee"]
            groups[key]["pay_info"] = r["_pay_info"]
            groups[key]["enroll_date"] = r["_enroll_date"]
            groups[key]["employee_registration_type"] = r.get("_employee_registration_type") or ""
            groups[key]["hours_list"].append(r["hours"])
            row_date = r["date"].date() if isinstance(r["date"], datetime) else r["date"]
            if isinstance(row_date, date):
                groups[key]["daily_hours_by_date"][row_date] += r["hours"]
            pt = r["_pay_info"]["pay_type"]
            daily_rate = r["_pay_info"].get("daily_wage") or 0
            hourly_rate = r["_pay_info"].get("hourly_wage") or 0
            monthly_sal = r["_pay_info"].get("monthly_salary") or 0
            h = r["hours"]
            # 規則：每日金額先算 raw，再四捨五入到整元，只把 rounded 加入加總（可驗證）
            special_property_mode = (
                payroll_type == "property"
                and ((r["_pay_info"].get("property_pay_mode") or "").strip().upper() in PROPERTY_PAY_MODES)
            )
            if special_property_mode:
                daily_amount_raw = 0.0
                daily_amount_rounded = 0
            else:
                if pt == "monthly":
                    if h >= 12:
                        daily_amount_raw = daily_rate
                    else:
                        daily_amount_raw = hourly_rate * h
                elif pt == "daily":
                    if h >= 12:
                        daily_amount_raw = daily_rate
                    else:
                        daily_amount_raw = hourly_rate * h
                else:
                    daily_amount_raw = hourly_rate * h
                daily_amount_rounded = int(round(daily_amount_raw, 0))
                groups[key]["daily_salaries"].append(daily_amount_rounded)
            if employee_name == DEBUG_EMPLOYEE:
                if "_debug_days" not in groups[key]:
                    groups[key]["_debug_days"] = []
                    groups[key]["_daily_raw"] = []
                day_idx = len(groups[key]["daily_salaries"])
                groups[key]["_daily_raw"].append(daily_amount_raw)
                if len(groups[key]["_debug_days"]) < 5:
                    groups[key]["_debug_days"].append({
                        "day": day_idx,
                        "hours": h,
                        "daily_amount_raw": daily_amount_raw,
                        "daily_amount_rounded": daily_amount_rounded,
                    })

        # 步驟1：產出各 (案場, 員工) 的工時與應發，不在此處算保險
        site_rows: List[dict] = []
        for (site_name, employee_name), data in groups.items():
            pay_info = data["pay_info"]
            total_hours = sum(data["hours_list"])
            pt = pay_info["pay_type"]
            special_property_mode = (
                payroll_type == "property"
                and ((pay_info.get("property_pay_mode") or "").strip().upper() in PROPERTY_PAY_MODES)
            )
            if not special_property_mode:
                gross = int(round(sum(data["daily_salaries"]), 0))
                monthly_sal = pay_info.get("monthly_salary") or 0
                if pt == "monthly" and total_hours >= 288:
                    gross = int(round(monthly_sal, 0))
                status = "未滿班"
                if pt == "monthly":
                    status = "滿班" if total_hours >= 288 else "未滿班"
                elif pt == "daily":
                    status = "日薪制"
                else:
                    status = "時薪制"
            else:
                gross = 0
                status = "未設定物業模式"
            site = await get_site_by_name(self.db, site_name)
            if not site:
                status = "案場未建檔"
            site_rows.append({
                "site": site_name,
                "employee": employee_name,
                "total_hours": total_hours,
                "gross": gross,
                "status": status,
                "pay_info": pay_info,
                "enroll_date": data.get("enroll_date"),
                "daily_hours_by_date": data.get("daily_hours_by_date") or {},
                "employee_registration_type": data.get("employee_registration_type") or "",
            })

        # 步驟2：按員工分組（同一年月下同一員工可能多案場）
        by_employee: dict[str, List[dict]] = defaultdict(list)
        for row in site_rows:
            by_employee[row["employee"]].append(row)

        # 步驟3：對每個員工只計算一次保險，並將扣款放在「該員工第一筆案場」
        bracket_import = await get_latest_bracket_import(self.db)
        results = []
        for employee_name, rows in by_employee.items():
            rows_sorted = sorted(rows, key=lambda r: (r["site"], r["employee"]))
            pay_info = rows_sorted[0]["pay_info"]
            enroll_d = rows_sorted[0]["enroll_date"]
            employee_registration_type = (rows_sorted[0].get("employee_registration_type") or "").strip().lower()

            property_employee_gross = 0
            property_employee_status = "未設定物業模式"
            property_site_gross: Dict[str, int] = {}
            property_mode = (pay_info.get("property_pay_mode") or "").strip().upper()
            property_special_mode = payroll_type == "property" and property_mode in PROPERTY_PAY_MODES
            if property_special_mode:
                merged_daily_hours_by_date: Dict[date, float] = defaultdict(float)
                per_site_daily_hours: Dict[str, Dict[date, float]] = defaultdict(lambda: defaultdict(float))
                for row in rows_sorted:
                    for d, day_hours in (row.get("daily_hours_by_date") or {}).items():
                        h = float(day_hours or 0)
                        merged_daily_hours_by_date[d] += h
                        per_site_daily_hours[row["site"]][d] += h
                if property_mode == "WEEKLY_2H":
                    property_site_gross, property_employee_status = self._build_property_weekly_site_distribution(
                        employee_name,
                        pay_info,
                        per_site_daily_hours,
                        year,
                        month,
                    )
                    property_employee_gross = sum(property_site_gross.values())
                else:
                    property_employee_gross, property_employee_status = self._build_property_result_for_employee(
                        employee_name,
                        pay_info,
                        merged_daily_hours_by_date,
                        year,
                        month,
                    )

            employee_has_gross = any((r.get("gross") or 0) > 0 for r in rows_sorted)
            if property_special_mode:
                employee_has_gross = property_employee_gross > 0
            insured_level = pay_info.get("insured_salary_level")

            labor_emp = 0.0
            health_emp = 0.0
            if payroll_type == "property" and not employee_has_gross:
                insured_level = None
            elif insured_level is None:
                if employee_name not in seen_level_err:
                    seen_level_err.add(employee_name)
                    errors.append(
                        {
                            "type": "missing_insured_level",
                            "employee_name": employee_name,
                            "message": f"員工【{employee_name}】未設定投保級距",
                        }
                    )
            else:
                if not bracket_import:
                    if (insured_level,) not in seen_bracket_err:
                        seen_bracket_err.add((insured_level,))
                        errors.append(
                            {
                                "type": "missing_bracket",
                                "insured_salary_level": insured_level,
                                "message": f"投保級距【{insured_level}】找不到級距表",
                            }
                        )
                else:
                    bracket = await get_bracket_by_level(self.db, bracket_import.id, int(insured_level))
                    if not bracket:
                        if (insured_level,) not in seen_bracket_err:
                            seen_bracket_err.add((insured_level,))
                            errors.append(
                                {
                                    "type": "missing_bracket",
                                    "insured_salary_level": insured_level,
                                    "message": f"投保級距【{insured_level}】找不到級距表",
                                }
                            )
                    else:
                        labor_emp = float(bracket.labor_employee)
                        health_emp = float(bracket.health_employee)

            group_enabled = pay_info.get("group_insurance_enabled", False)
            group_fee = pay_info.get("group_insurance_fee", 0) or 0
            group_ins, group_days, group_monthly_fee = _calc_group_insurance(
                enroll_d, year, month, group_enabled, group_fee
            )
            if payroll_type == "property" and not employee_has_gross:
                group_ins, group_days, group_monthly_fee = 0.0, 0, 0.0
            if group_enabled and enroll_d is None and employee_name not in seen_enroll_err and not (payroll_type == "property" and not employee_has_gross):
                seen_enroll_err.add(employee_name)
                errors.append(
                    {
                        "type": "missing_enroll_date",
                        "employee_name": employee_name,
                        "message": f"員工【{employee_name}】未設定加保日期，團保無法計算",
                    }
                )

            self_pen6 = 0
            if pay_info.get("pension_self_6") and insured_level is not None:
                self_pen6 = int(round(int(insured_level) * 0.06, 0))

            cross_site_note = " 跨案場計算（保險僅扣一次）" if len(rows_sorted) > 1 else ""
            deduction_owner_index = 0
            if property_special_mode:
                if property_mode == "WEEKLY_2H":
                    for idx, row in enumerate(rows_sorted):
                        if property_site_gross.get(row["site"], 0) > 0:
                            deduction_owner_index = idx
                            break
                else:
                    deduction_owner_index = 0

            for i, r in enumerate(rows_sorted):
                row_gross = r["gross"]
                row_status = r["status"]
                if property_special_mode:
                    if property_mode == "WEEKLY_2H":
                        row_gross = property_site_gross.get(r["site"], 0)
                    else:
                        row_gross = property_employee_gross if i == 0 else 0
                    row_status = property_employee_status
                force_zero = payroll_type == "property" and row_gross <= 0
                if i == deduction_owner_index:
                    labor_row = int(round(labor_emp, 0))
                    health_row = int(round(health_emp, 0))
                    group_row = int(round(group_ins, 0))
                    self_pen6_row = self_pen6
                else:
                    labor_row = 0
                    health_row = 0
                    group_row = 0
                    self_pen6_row = 0
                if force_zero:
                    labor_row = 0
                    health_row = 0
                    group_row = 0
                    self_pen6_row = 0
                deductions_total = int(round(labor_row + health_row + group_row + self_pen6_row, 0))
                net = 0 if force_zero else int(round(row_gross - deductions_total, 0))
                status = row_status + cross_site_note
                if employee_registration_type and employee_registration_type != current_type:
                    status += f"（來源：{_registration_type_label(employee_registration_type)}）"

                row_out = {
                    "site": r["site"],
                    "employee": employee_name,
                    "pay_type": pay_info["pay_type"],
                    "total_hours": round(r["total_hours"], 2),
                    "gross_salary": row_gross,
                    "labor_insurance_employee": labor_row,
                    "health_insurance_employee": health_row,
                    "group_insurance": group_row,
                    "self_pension_6": self_pen6_row,
                    "deductions_total": deductions_total,
                    "net_salary": net,
                    "total_salary": net,
                    "status": status,
                    "year": year,
                    "month": month,
                    "type": payroll_type,
                    "source_payroll_type": employee_registration_type or current_type,
                }
                row_out["enroll_date"] = enroll_d.isoformat() if enroll_d else None
                row_out["group_insurance_days"] = group_days
                row_out["group_insurance_monthly_fee"] = int(round(group_monthly_fee, 0))
                logger.debug(
                    "payroll employee=%s site=%s labor=%s health=%s group=%s self_pen6=%s deductions_total=%s",
                    employee_name, r["site"], labor_row, health_row, group_row, self_pen6_row, deductions_total,
                )
                results.append(row_out)

        results.sort(key=lambda x: (x["site"], x["employee"]))
        debug = None
        for (site_name, emp_name) in sorted(groups.keys()):
            if emp_name != DEBUG_EMPLOYEE:
                continue
            data = groups[(site_name, emp_name)]
            if "_debug_days" not in data:
                continue
            gross_final = None
            for row in results:
                if row["site"] == site_name and row["employee"] == emp_name:
                    gross_final = row["gross_salary"]
                    break
            pay_info = data["pay_info"]
            debug = {
                "employee": emp_name,
                "pay_type": pay_info["pay_type"],
                "monthly": pay_info.get("monthly_salary"),
                "daily_rate": pay_info.get("daily_wage"),
                "hourly_rate": pay_info.get("hourly_wage"),
                "first_5_days": data["_debug_days"][:5],
                "gross_by_sum_raw": int(round(sum(data["_daily_raw"]), 0)),
                "gross_by_sum_rounded_daily": int(round(sum(data["daily_salaries"]), 0)),
                "gross_final": gross_final,
            }
            break
        return results, errors, debug


def compute_test_rounding() -> dict:
    """
    內建測試：驗證「每日先四捨五入到整元再加總」規則（不讀 Excel、不碰 DB）。
    固定：pay_type=daily, daily_rate=10875, hourly_rate=round(10875/12,0)=906（整元）, hours_list=[11]*30
    預期：每日 round(906*11,0)=9966（整元），gross=9966*30=298980
    """
    pay_type = "daily"
    daily_rate = 10875
    hourly_rate = int(round(daily_rate / 12, 0))  # 906 整元
    hours_list = [11] * 30
    daily_amounts_rounded = []
    for h in hours_list:
        raw = hourly_rate * h
        daily_amounts_rounded.append(int(round(raw, 0)))
    gross = int(round(sum(daily_amounts_rounded), 0))
    expected_gross = 298980
    first_5 = [
        {"day": i + 1, "hours": h, "daily_amount_raw": hourly_rate * h, "daily_amount_rounded": daily_amounts_rounded[i]}
        for i, h in enumerate(hours_list[:5])
    ]
    return {
        "pay_type": pay_type,
        "daily_rate": daily_rate,
        "hourly_rate": hourly_rate,
        "hours_list_length": len(hours_list),
        "first_5_days": first_5,
        "gross": gross,
        "expected_gross": expected_gross,
        "pass": gross == expected_gross,
    }
