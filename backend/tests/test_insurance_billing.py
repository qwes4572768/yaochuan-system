"""
試算計費整合單元測試。
測試：不傳加退保時整月；傳 year/month/enroll_date/cancel_date 時依健保月比例與勞保等按天數比例。
情境：跨月、月底加保、非月底退保、身障減免、65 歲減免（與 health_reduction 搭配）。
"""
from datetime import date
from decimal import Decimal
import pytest

from app.services.insurance_calc import estimate_insurance


def test_estimate_full_month_without_dates():
    """不傳 year/month/enroll_date：整月計費"""
    r = estimate_insurance(
        dependent_count=0,
        insured_salary_level=Decimal("26400"),
    )
    assert r.labor_insurance.total > 0
    assert r.health_insurance.total > 0
    assert r.occupational_accident.total > 0
    assert r.labor_pension.total > 0


def test_estimate_proration_mid_month_enroll():
    """月中加保、無退保：勞保等按天數比例，健保整月（非月底退保）"""
    # 2025/1/15 加保，1 月：勞保等 17 天，健保整月
    r = estimate_insurance(
        dependent_count=0,
        insured_salary_level=Decimal("26400"),
        year=2025,
        month=1,
        enroll_date=date(2025, 1, 15),
        cancel_date=None,
    )
    # 勞保整月約 3036 * (17/30) 約 1720
    assert r.labor_insurance.total < Decimal("2500")
    assert r.labor_insurance.total > Decimal("1500")
    assert r.health_insurance.total > 0


def test_estimate_health_zero_when_cancel_not_last_day():
    """退保日非當月最後一日：當月健保 0"""
    r = estimate_insurance(
        dependent_count=0,
        insured_salary_level=Decimal("26400"),
        year=2025,
        month=1,
        enroll_date=date(2025, 1, 1),
        cancel_date=date(2025, 1, 15),
    )
    assert r.health_insurance.total == Decimal("0")
    assert r.health_insurance.employer == Decimal("0")
    assert r.health_insurance.employee == Decimal("0")
    # 勞保等仍按天數（14 天）
    assert r.labor_insurance.total > 0
    assert r.labor_insurance.total < Decimal("2000")


def test_estimate_health_full_when_enroll_last_day():
    """加保日為當月最後一日：該月健保整月"""
    r = estimate_insurance(
        dependent_count=0,
        insured_salary_level=Decimal("26400"),
        year=2025,
        month=1,
        enroll_date=date(2025, 1, 31),
        cancel_date=None,
    )
    assert r.health_insurance.total > 0
    # 勞保僅 1 天
    assert r.labor_insurance.total > 0
    assert r.labor_insurance.total < Decimal("150")


def test_estimate_cross_month_full_january():
    """跨月：1 月整月在保，勞保等 31 天、健保整月"""
    r = estimate_insurance(
        dependent_count=0,
        insured_salary_level=Decimal("26400"),
        year=2025,
        month=1,
        enroll_date=date(2024, 12, 10),
        cancel_date=date(2025, 2, 5),
    )
    assert r.health_insurance.total > 0
    # 1 月 31 天，勞保應接近整月略多（31/30）
    assert r.labor_insurance.total > Decimal("3000")


def test_estimate_with_persons_disability_reduction():
    """傳入 persons 且眷屬身障：健保明細有減免後個人負擔"""
    persons = [
        {"name": "員工", "is_employee": True, "birth_date": "1990-01-01", "city": None, "disability_level": None},
        {"name": "眷屬", "is_employee": False, "birth_date": "1985-01-01", "city": "高雄市", "disability_level": "輕度"},
    ]
    r = estimate_insurance(
        dependent_count=1,
        insured_salary_level=Decimal("26400"),
        persons=persons,
    )
    assert r.health_insurance_breakdown is not None
    assert len(r.health_insurance_breakdown.detail) == 2
    # 眷屬應有減免（輕度 0.75）
    reduced = r.health_insurance_breakdown.reduced_personal_total
    original = r.health_insurance_breakdown.original_personal_total
    assert reduced < original


def test_estimate_with_persons_senior_65_reduction():
    """傳入 persons 且眷屬 65 歲桃園市：健保個人負擔 0（該眷屬）"""
    persons = [
        {"name": "員工", "is_employee": True, "birth_date": "1990-01-01", "city": None, "disability_level": None},
        {"name": "眷屬", "is_employee": False, "birth_date": "1958-01-01", "city": "桃園市", "disability_level": None},
    ]
    r = estimate_insurance(
        dependent_count=1,
        insured_salary_level=Decimal("26400"),
        persons=persons,
        year=2025,
        month=6,
        enroll_date=date(2025, 1, 1),
        cancel_date=None,
    )
    assert r.health_insurance_breakdown is not None
    # 眷屬 65 歲桃園市應 0（1958 出生在 2023 後皆滿 65）
    detail = {row.name: row.reduced_personal for row in r.health_insurance_breakdown.detail}
    assert detail.get("眷屬", Decimal("-1")) == Decimal("0")
