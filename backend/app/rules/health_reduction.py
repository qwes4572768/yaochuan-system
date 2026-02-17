"""
健保分攤/減免規則：依 config/health_reduction_rules.yaml 套用，可擴充。
回傳每人適用之倍率（0~1）與套用規則說明，不寫死在頁面。
"""
from pathlib import Path
from datetime import date
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import yaml


def _load_rules() -> list:
    # 從 app/rules 往上一層到 app、再往上一層到 backend，取 config
    path = Path(__file__).resolve().parents[2] / "config" / "health_reduction_rules.yaml"
    if not path.exists():
        return _default_rules()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("rules", _default_rules())


def _default_rules() -> list:
    """內建預設（與 YAML 同），無檔案時使用"""
    return [
        {
            "id": "senior_dependent_city_zero",
            "name": "六都 65 歲以上眷屬健保補助",
            "applies_to": "dependent_only",
            "condition": {"type": "senior_in_cities", "min_age": 65, "cities": ["桃園市", "台北市"]},
            "result": {"multiplier": 0},
        },
        {
            "id": "disability_discount",
            "name": "身障健保補助",
            "applies_to": "both",
            "condition": {"type": "has_disability_level"},
            "result_by_level": {"輕度": 0.75, "中度": 0.5, "重度": 0, "極重度": 0},
            "default_multiplier": 1,
        },
    ]


def _age_at(birth_date: Optional[date], at: date) -> Optional[int]:
    if not birth_date:
        return None
    age = at.year - birth_date.year
    if (at.month, at.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _rule_applies_to_person(rule: dict, is_employee: bool) -> bool:
    at = rule.get("applies_to", "both")
    if at == "both":
        return True
    if at == "employee_only":
        return is_employee
    if at == "dependent_only":
        return not is_employee
    return True


def _condition_match(rule: dict, is_employee: bool, birth_date: Optional[date], city: Optional[str], disability_level: Optional[str], at_date: date) -> bool:
    cond = rule.get("condition") or {}
    ctype = cond.get("type")
    if ctype == "senior_in_cities":
        if is_employee:
            return False
        age = _age_at(birth_date, at_date)
        if age is None:
            return False
        cities = cond.get("cities") or []
        return age >= cond.get("min_age", 65) and (city or "") in cities
    if ctype == "has_disability_level":
        return bool(disability_level and (disability_level in (rule.get("result_by_level") or {})))
    return False


def _get_multiplier(rule: dict, disability_level: Optional[str]) -> Decimal:
    if "result" in rule:
        return Decimal(str(rule["result"].get("multiplier", 1)))
    by_level = rule.get("result_by_level") or {}
    if disability_level and disability_level in by_level:
        return Decimal(str(by_level[disability_level]))
    return Decimal(str(rule.get("default_multiplier", 1)))


def apply_health_reduction(
    is_employee: bool,
    birth_date: Optional[date] = None,
    city: Optional[str] = None,
    disability_level: Optional[str] = None,
    at_date: Optional[date] = None,
) -> Tuple[Decimal, List[str]]:
    """
    套用健保減免規則，回傳 (個人負擔倍率 0~1, 套用規則名稱列表)。
    多條符合時取倍率最低（最優），並記錄所有套用的規則名稱。
    """
    at_date = at_date or date.today()
    rules = _load_rules()
    best_multiplier = Decimal("1")
    applied_names: List[str] = []

    for rule in rules:
        if not _rule_applies_to_person(rule, is_employee):
            continue
        if not _condition_match(rule, is_employee, birth_date, city, disability_level, at_date):
            continue
        mult = _get_multiplier(rule, disability_level)
        best_multiplier = min(best_multiplier, mult)
        applied_names.append(rule.get("name", rule.get("id", "")))

    # 若未套用任何規則，回傳 1（無減免）
    if not applied_names:
        return (Decimal("1"), [])
    return (best_multiplier, applied_names)


def get_health_reduction_rules() -> List[Dict[str, Any]]:
    """取得目前載入之健保減免規則（供後台檢視/擴充）"""
    return _load_rules()
