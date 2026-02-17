"""
計費天數與月比例純函式單元測試。
測試：跨月加退保、月底加保、非月底退保、天數計算（含加保日、不含退保日）。
"""
from datetime import date
from decimal import Decimal
import pytest

from app.services.billing_days import (
    first_day_of_month,
    last_day_of_month,
    is_last_day_of_month,
    get_insured_days_in_month,
    health_insurance_month_ratio,
    labor_insurance_month_fee,
    occupational_accident_month_fee,
    group_insurance_month_fee,
    labor_pension_month_fee,
    days_in_month,
)


# ---------- 天數計算：含加保日、不含退保日 ----------


def test_insured_days_single_month_no_cancel():
    """當月加保、無退保：從加保日到月底皆算（含加保日）"""
    # 1/15 加保，無退保 → 1 月 15~31 = 17 天
    assert get_insured_days_in_month(2025, 1, date(2025, 1, 15), None) == 17


def test_insured_days_single_month_with_cancel():
    """當月加保、當月退保：含加保日、不含退保日"""
    # 1/15 加保、1/20 退保 → 15,16,17,18,19 = 5 天
    assert get_insured_days_in_month(2025, 1, date(2025, 1, 15), date(2025, 1, 20)) == 5


def test_insured_days_cross_month():
    """跨月：加保在上月、退保在下月，當月整月計"""
    # 2024/12/10 加保、2025/2/5 退保 → 2025/1 整月 31 天
    assert get_insured_days_in_month(2025, 1, date(2024, 12, 10), date(2025, 2, 5)) == 31


def test_insured_days_enroll_after_month():
    """加保日在當月之後：當月 0 天"""
    assert get_insured_days_in_month(2025, 1, date(2025, 2, 1), None) == 0


def test_insured_days_cancel_before_month():
    """退保日在當月之前：當月 0 天"""
    assert get_insured_days_in_month(2025, 2, date(2025, 1, 1), date(2025, 1, 31)) == 0


def test_insured_days_last_day_of_month_enroll():
    """月底加保、無退保：當月僅最後一天 1 天"""
    assert get_insured_days_in_month(2025, 1, date(2025, 1, 31), None) == 1


def test_insured_days_non_last_day_cancel():
    """月中退保：當月只算到退保日前一天（不含退保日）"""
    # 1/1 加保、1/15 退保 → 1~14 = 14 天
    assert get_insured_days_in_month(2025, 1, date(2025, 1, 1), date(2025, 1, 15)) == 14


def test_insured_days_cancel_on_last_day():
    """退保日為當月最後一天：當月含到最後一天（區間為 [enroll, cancel)，不含 cancel 日，故最後一天不算？）
    規則：含加保日、不含退保日。退保 1/31 表示 1/31 當天不在保，所以 1 月有效為 1/1~1/30 = 30 天。"""
    assert get_insured_days_in_month(2025, 1, date(2025, 1, 1), date(2025, 1, 31)) == 30


# ---------- 健保：月底加保整月、非月底退保當月 0 ----------


def test_health_ratio_full_month_in_range():
    """在加保區間內、無退保：整月比例 1"""
    assert health_insurance_month_ratio(2025, 1, date(2025, 1, 1), None) == Decimal("1")
    assert health_insurance_month_ratio(2025, 1, date(2024, 12, 15), None) == Decimal("1")


def test_health_ratio_enroll_last_day_of_month():
    """加保日為當月最後一日：該月仍算整月 → 比例 1"""
    assert health_insurance_month_ratio(2025, 1, date(2025, 1, 31), None) == Decimal("1")


def test_health_ratio_cancel_not_last_day():
    """退保日不是當月最後一日：該月健保 0 → 比例 0"""
    assert health_insurance_month_ratio(2025, 1, date(2025, 1, 1), date(2025, 1, 15)) == Decimal("0")
    assert health_insurance_month_ratio(2025, 1, date(2024, 12, 1), date(2025, 1, 20)) == Decimal("0")


def test_health_ratio_cancel_last_day_of_month():
    """退保日為當月最後一日：該月仍算整月 → 比例 1"""
    assert health_insurance_month_ratio(2025, 1, date(2025, 1, 1), date(2025, 1, 31)) == Decimal("1")


def test_health_ratio_enroll_after_month():
    """加保日在當月之後：比例 0"""
    assert health_insurance_month_ratio(2025, 1, date(2025, 2, 1), None) == Decimal("0")


def test_health_ratio_cancel_before_month():
    """退保日在當月之前：比例 0"""
    assert health_insurance_month_ratio(2025, 2, date(2025, 1, 1), date(2025, 1, 31)) == Decimal("0")


# ---------- 勞保/職災/團保/勞退：整月在保收整月，未滿整月 (月費/30)*天數 ----------


def test_days_in_month():
    """當月日曆天數"""
    assert days_in_month(2025, 1) == 31
    assert days_in_month(2026, 2) == 28


def test_labor_insurance_month_fee_prorated():
    """未滿整月：勞保 (月費/30)*加保天數"""
    # 月勞保 300，1 月加保 15~31 共 17 天 → (300/30)*17 = 170
    fee = labor_insurance_month_fee(2025, 1, date(2025, 1, 15), None, Decimal("300"))
    assert fee == Decimal("170.00")


def test_labor_insurance_month_fee_full_month():
    """整月在保：收整月費用（不除以 30 再乘當月天數）"""
    # 1 月整月 31 天在保 → 收整月 300
    fee = labor_insurance_month_fee(2025, 1, date(2024, 12, 1), date(2025, 2, 1), Decimal("300"))
    assert fee == Decimal("300.00")


def test_labor_insurance_month_fee_february_full_month():
    """2 月整月 28 天在保 → 收整月（不以 28/30 比例）"""
    fee = labor_insurance_month_fee(2026, 2, date(2026, 1, 30), None, Decimal("300"))
    assert fee == Decimal("300.00")


def test_occupational_accident_month_fee():
    """職災費：未滿整月 (月費/30)*天數"""
    fee = occupational_accident_month_fee(2025, 1, date(2025, 1, 10), date(2025, 1, 20), Decimal("60"))
    assert fee == Decimal("20.00")  # 10 天，(60/30)*10 = 20


def test_group_insurance_month_fee():
    """團保：整月在保收整月"""
    fee = group_insurance_month_fee(2025, 1, date(2025, 1, 1), None, Decimal("150"))
    assert fee == Decimal("150.00")  # 1 月 31 天在保 → 整月 150


def test_labor_pension_month_fee():
    """勞退：未滿整月 (月費/30)*天數"""
    fee = labor_pension_month_fee(2025, 1, date(2025, 1, 16), None, Decimal("180"))
    assert fee == Decimal("96.00")  # 16~31 = 16 天，(180/30)*16 = 96


# ---------- 輔助 ----------


def test_is_last_day_of_month():
    assert is_last_day_of_month(date(2025, 1, 31)) is True
    assert is_last_day_of_month(date(2025, 1, 30)) is False
    assert is_last_day_of_month(date(2024, 2, 29)) is True
