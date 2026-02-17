"""
計費天數與月比例之純函式（勞保/職災/團保/勞退按天數，健保按月規則）。

加退保日規則（一致且明確定義）：
- 含加保日、不含退保日。即保險有效區間為 [enroll_date, cancel_date)。
- 當月「加保天數」= 該月內滿足 enroll_date <= 日 < cancel_date 的天數；
  無退保日時，當月視為到月底皆有效（即到 last_day 含）。
- 例：加保 1/15、退保 1/20 → 1 月天數 = 15,16,17,18,19 = 5 天。
- 例：加保 1/15、無退保 → 1 月天數 = 15~31 = 17 天。
"""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# ---------- 天數計算（含加保日、不含退保日） ----------


def first_day_of_month(year: int, month: int) -> date:
    """指定年月的第一天"""
    return date(year, month, 1)


def last_day_of_month(year: int, month: int) -> date:
    """指定年月的最後一天"""
    _, last = monthrange(year, month)
    return date(year, month, last)


def is_last_day_of_month(d: date) -> bool:
    """是否為該月最後一天"""
    return d.day == monthrange(d.year, d.month)[1]


def get_insured_days_in_month(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date] = None,
) -> int:
    """
    當月加保天數（含加保日、不含退保日）。
    區間 [enroll_date, cancel_date)；無退保日時視為當月到月底皆有效。
    """
    first = first_day_of_month(year, month)
    last = last_day_of_month(year, month)
    # 當月有效區間起日（含）：取 enroll 與當月首日較晚者
    start = max(enroll_date, first)
    # 當月有效區間訖日（不含）：有退保且退保在本月內則為退保日，否則為當月最後一日+1
    if cancel_date is not None and cancel_date <= last:
        end_exclusive = cancel_date  # 不含退保日
    else:
        end_exclusive = last + timedelta(days=1)
    if start >= end_exclusive:
        return 0
    return (end_exclusive - start).days


# ---------- 健保：以月為單位，兩條特殊規則 ----------


def health_insurance_month_ratio(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date] = None,
) -> Decimal:
    """
    健保當月計費比例（0 或 1）。
    - 加保日若為當月最後一日：該月仍算整月費用 → 比例 1。
    - 退保日若不是當月最後一日：該月健保費用為 0 → 比例 0。
    - 其餘在加保區間內之月份為整月 → 比例 1。
    """
    last = last_day_of_month(year, month)
    first = first_day_of_month(year, month)
    # 未在加保區間：enroll 尚未開始或已退保在當月之前
    if enroll_date > last:
        return Decimal("0")
    if cancel_date is not None and cancel_date < first:
        return Decimal("0")
    # 退保日若不是當月最後一日：該月健保費用為 0
    if cancel_date is not None:
        cancel_in_this_month = first <= cancel_date <= last
        if cancel_in_this_month and not is_last_day_of_month(cancel_date):
            return Decimal("0")
    # 加保日若為當月最後一日：該月仍算整月
    if enroll_date == last:
        return Decimal("1")
    # 當月有加保且未因「非月底退保」歸零 → 整月
    if enroll_date <= last and (cancel_date is None or cancel_date > last or is_last_day_of_month(cancel_date)):
        return Decimal("1")
    return Decimal("0")


# ---------- 勞保/職災/團保/勞退：按天數比例 ----------


# 未滿整月時，日費率分母固定 30 天（勞保總數/30*天數）
PRORATION_DAYS_DENOMINATOR = 30


def days_in_month(year: int, month: int) -> int:
    """當月日曆天數（如 2 月 28 天、1 月 31 天）"""
    return monthrange(year, month)[1]


def _prorated_month_fee(
    monthly_total: Decimal,
    insured_days: int,
    year: int,
    month: int,
) -> Decimal:
    """
    當月費用：若加保天數 = 當月日曆天數 → 收整月；否則 (月費/30)*加保天數。
    例：2 月 28 天在保 → 整月；只上 15 天 → 月費/30*15。
    """
    d_in_month = days_in_month(year, month)
    if insured_days >= d_in_month:
        return monthly_total
    return (monthly_total / Decimal(PRORATION_DAYS_DENOMINATOR) * Decimal(insured_days)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def labor_insurance_month_fee(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date],
    monthly_labor_total: Decimal,
) -> Decimal:
    """當月勞保費：整月在保收整月；未滿整月則 (月費/30)*加保天數。含加保日、不含退保日。"""
    days = get_insured_days_in_month(year, month, enroll_date, cancel_date)
    return _prorated_month_fee(monthly_labor_total, days, year, month)


def occupational_accident_month_fee(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date],
    monthly_occ_total: Decimal,
) -> Decimal:
    """當月職災費：整月在保收整月；未滿整月則 (月費/30)*加保天數。"""
    days = get_insured_days_in_month(year, month, enroll_date, cancel_date)
    return _prorated_month_fee(monthly_occ_total, days, year, month)


def group_insurance_month_fee(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date],
    monthly_group_total: Decimal,
) -> Decimal:
    """當月團保費：整月在保收整月；未滿整月則 (月費/30)*加保天數。"""
    days = get_insured_days_in_month(year, month, enroll_date, cancel_date)
    return _prorated_month_fee(monthly_group_total, days, year, month)


def labor_pension_month_fee(
    year: int,
    month: int,
    enroll_date: date,
    cancel_date: Optional[date],
    monthly_pension_total: Decimal,
) -> Decimal:
    """當月勞退 6%：整月在保收整月；未滿整月則 (月費/30)*加保天數。"""
    days = get_insured_days_in_month(year, month, enroll_date, cancel_date)
    return _prorated_month_fee(monthly_pension_total, days, year, month)
