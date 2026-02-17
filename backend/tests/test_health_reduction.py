"""
健保減免規則單元測試。
測試：身障減免（輕/中/重/極重度）、65 歲以上眷屬（桃園市/台北市）減免。
"""
from datetime import date
from decimal import Decimal
import pytest

from app.rules.health_reduction import apply_health_reduction


def test_no_reduction_without_condition():
    """無身障、非 65 歲眷屬：倍率 1（無減免）"""
    mult, names = apply_health_reduction(
        is_employee=True,
        birth_date=date(1990, 5, 1),
        city=None,
        disability_level=None,
    )
    assert mult == Decimal("1")
    assert names == []

    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(2000, 1, 1),
        city="新北市",
        disability_level=None,
    )
    assert mult == Decimal("1")
    assert names == []


def test_disability_light():
    """身障輕度：個人負擔 0.75"""
    mult, names = apply_health_reduction(
        is_employee=True,
        birth_date=date(1990, 1, 1),
        city=None,
        disability_level="輕度",
    )
    assert mult == Decimal("0.75")
    assert "身障健保補助" in names or "disability" in str(names).lower()


def test_disability_moderate():
    """身障中度：個人負擔 0.5"""
    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(1980, 1, 1),
        city="高雄市",
        disability_level="中度",
    )
    assert mult == Decimal("0.5")


def test_disability_severe():
    """身障重度：個人負擔 0"""
    mult, names = apply_health_reduction(
        is_employee=True,
        disability_level="重度",
    )
    assert mult == Decimal("0")


def test_disability_very_severe():
    """身障極重度：個人負擔 0"""
    mult, names = apply_health_reduction(
        is_employee=False,
        disability_level="極重度",
    )
    assert mult == Decimal("0")


def test_senior_65_taoyuan_dependent():
    """65 歲以上眷屬、桃園市：個人負擔 0（六都 65 歲眷屬補助）"""
    # 出生日設為 1959/6/1，在 2025/6/1 滿 65 歲；at_date 用 2025/6/15
    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(1959, 6, 1),
        city="桃園市",
        disability_level=None,
        at_date=date(2025, 6, 15),
    )
    assert mult == Decimal("0")
    assert any("65" in n or "眷屬" in n or "桃園" in n or "六都" in n for n in names)


def test_senior_65_taipei_dependent():
    """65 歲以上眷屬、台北市：個人負擔 0"""
    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(1958, 1, 1),
        city="台北市",
        disability_level=None,
        at_date=date(2025, 1, 15),
    )
    assert mult == Decimal("0")


def test_senior_64_no_city_reduction():
    """未滿 65 歲眷屬：不適用 65 歲補助"""
    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(1961, 1, 1),
        city="桃園市",
        disability_level=None,
        at_date=date(2025, 1, 1),
    )
    # 1961 出生，2025/1/1 時 63 歲
    assert mult == Decimal("1")
    assert not any("65" in n for n in names)


def test_senior_65_other_city_no_reduction():
    """65 歲以上眷屬但非桃園/台北：不適用該條補助"""
    mult, names = apply_health_reduction(
        is_employee=False,
        birth_date=date(1958, 1, 1),
        city="新北市",
        disability_level=None,
        at_date=date(2025, 1, 1),
    )
    assert mult == Decimal("1")
