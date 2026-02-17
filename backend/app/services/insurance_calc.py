"""勞健保/職災/團保/勞退試算 - 規則來自設定表(DB)或 YAML 預設；健保分攤/減免集中於 rules 模組。
計費依加退保日：健保按月規則（月底加保整月、非月底退保當月0）；勞保/職災/勞退按天數比例（含加保日、不含退保日）；團保為固定月費、全由員工負擔（不按天數）。"""
from pathlib import Path
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List

import yaml

from app.schemas import ItemBreakdown, InsuranceEstimateResponse, HealthInsuranceBreakdown, HealthInsuranceDetailRow
from app.rules.health_reduction import apply_health_reduction
from app.config import settings
from app.services.billing_days import (
    days_in_month,
    get_insured_days_in_month,
    health_insurance_month_ratio,
    labor_insurance_month_fee,
    occupational_accident_month_fee,
    labor_pension_month_fee,
)


def _load_rules_from_yaml() -> dict:
    """預設規則：config/insurance_rules.yaml（未在 DB 設定時使用）"""
    path = Path(__file__).resolve().parents[2] / "config" / "insurance_rules.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _find_bracket(salary: Decimal, brackets: list) -> Decimal:
    """依薪資找級距對應的投保薪資"""
    s = float(salary)
    for low, high, level in brackets:
        if low <= s <= high:
            return Decimal(str(level))
    if brackets:
        last = brackets[-1]
        return Decimal(str(last[2]))
    return salary


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt(n: Decimal) -> str:
    """數字格式化為千分位，小數至多兩位"""
    v = float(n)
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def get_brackets(rules: Optional[Dict[str, Any]] = None) -> list:
    """取得級距列表 [ (low, high, level), ... ] 供下拉選單或輸入金額對應"""
    rules = rules if rules is not None else _load_rules_from_yaml()
    lab = rules.get("labor_insurance", {})
    return lab.get("brackets", [])


def salary_to_level(salary: Decimal, rules: Optional[Dict[str, Any]] = None) -> Decimal:
    """輸入金額後自動對應級距"""
    brackets = get_brackets(rules)
    return _find_bracket(salary, brackets)


def _parse_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except Exception:
            return None
    return None


def estimate_insurance(
    dependent_count: int = 0,
    rules: Optional[Dict[str, Any]] = None,
    insured_salary_level: Optional[Decimal] = None,
    salary_input: Optional[Decimal] = None,
    group_insurance_fee: Optional[Decimal] = None,
    persons: Optional[List[Dict[str, Any]]] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    enroll_date: Optional[date] = None,
    cancel_date: Optional[date] = None,
) -> InsuranceEstimateResponse:
    """
    試算：勞保、健保（本人+眷屬）、職災、勞退6%、團保。
    眷屬超過 3 人以 3 人計（健保）。
    persons: 若有傳入（員工+眷屬每人 name, is_employee, birth_date, city, disability_level），
    則健保會依 rules 模組計算「原本個人負擔」與「減免後個人負擔」、「公司負擔」明細。
    當 year, month, enroll_date 皆有值時，依加退保日計費：
    - 健保：月底加保整月、非月底退保當月 0；其餘整月。
    - 勞保/職災/團保/勞退：按當月加保天數比例（含加保日、不含退保日）。
    未傳 year/month/enroll_date 時，視為整月計費。
    """
    rules = rules if rules is not None else _load_rules_from_yaml()
    lab = rules.get("labor_insurance", {})
    health = rules.get("health_insurance", {})
    occ = rules.get("occupational_accident", {})
    pension = rules.get("labor_pension", {})
    group = rules.get("group_insurance", {})

    # 是否依加退保日按比例計費（需同時有 year, month, enroll_date）
    enroll_d = enroll_date if isinstance(enroll_date, date) else _parse_date(enroll_date)
    cancel_d = cancel_date if isinstance(cancel_date, date) else _parse_date(cancel_date)
    use_proration = year is not None and month is not None and enroll_d is not None

    lab_brackets = lab.get("brackets", [])
    if insured_salary_level is not None and insured_salary_level > 0:
        lab_level = insured_salary_level
    elif salary_input is not None and salary_input > 0:
        lab_level = _find_bracket(salary_input, lab_brackets)
    else:
        lab_level = Decimal("26400")
    health_level = lab_level
    max_dep = health.get("max_dependents_count", 3)
    dep_count = min(dependent_count, max_dep)
    if persons is not None and len(persons) > 0:
        n_emp = sum(1 for p in persons if p.get("is_employee"))
        n_dep = len(persons) - n_emp
        dep_count = min(n_dep, max_dep)

    # 勞保
    lab_rate = Decimal(str(lab.get("rate", 0.115)))
    lab_total = _round2(lab_level * lab_rate)
    lab_emp_ratio = Decimal(str(lab.get("employer_ratio", 0.7)))
    lab_work_ratio = Decimal(str(lab.get("employee_ratio", 0.2)))
    if use_proration:
        lab_month_total = labor_insurance_month_fee(year, month, enroll_d, cancel_d, lab_total)
        labor_insurance = ItemBreakdown(
            name="勞保",
            employer=_round2(lab_month_total * lab_emp_ratio),
            employee=_round2(lab_month_total * lab_work_ratio),
            total=lab_month_total,
        )
    else:
        labor_insurance = ItemBreakdown(
            name="勞保",
            employer=_round2(lab_total * lab_emp_ratio),
            employee=_round2(lab_total * lab_work_ratio),
            total=lab_total,
        )

    # 健保：本人 + 眷屬（每人同級距）；若有 persons 則套用減免規則並輸出明細
    health_rate = Decimal(str(health.get("rate", 0.0517)))
    health_emp_ratio = Decimal(str(health.get("employer_ratio", 0.6)))
    health_work_ratio = Decimal(str(health.get("employee_ratio", 0.3)))
    health_people = 1 + dep_count
    base_per_person = _round2(health_level * health_rate)
    health_total = _round2(base_per_person * Decimal(health_people))
    health_employer = _round2(health_total * health_emp_ratio)
    original_personal_per_person = _round2(base_per_person * health_work_ratio)

    # 健保當月比例（依加退保日：月底加保整月、非月底退保當月 0）
    health_ratio = health_insurance_month_ratio(year, month, enroll_d, cancel_d) if use_proration else Decimal("1")

    health_insurance_breakdown: Optional[HealthInsuranceBreakdown] = None
    if persons is not None and len(persons) > 0:
        # 取 1 本人 + 最多 dep_count 眷屬（本人放最前）
        emp_list = [p for p in persons if p.get("is_employee")]
        dep_list = [p for p in persons if not p.get("is_employee")][:dep_count]
        persons_to_use = (emp_list[:1] or []) + dep_list
        detail_rows: List[HealthInsuranceDetailRow] = []
        reduced_total = Decimal("0")
        original_total = Decimal("0")
        for p in persons_to_use:
            name = p.get("name") or "—"
            is_emp = bool(p.get("is_employee"))
            role = "本人" if is_emp else "眷屬"
            bd = _parse_date(p.get("birth_date"))
            city = p.get("city") or ""
            d_level = p.get("disability_level") or ""
            mult, rule_names = apply_health_reduction(is_employee=is_emp, birth_date=bd, city=city, disability_level=d_level)
            orig = original_personal_per_person
            reduced = _round2(orig * mult)
            original_total += orig
            reduced_total += reduced
            detail_rows.append(
                HealthInsuranceDetailRow(
                    name=name,
                    role=role,
                    rule_applied=rule_names,
                    original_personal=orig,
                    reduced_personal=reduced,
                )
            )
        health_insurance_breakdown = HealthInsuranceBreakdown(
            original_personal_total=_round2(original_total * health_ratio),
            reduced_personal_total=_round2(reduced_total * health_ratio),
            employer_total=_round2(health_employer * health_ratio),
            detail=[HealthInsuranceDetailRow(
                name=r.name,
                role=r.role,
                rule_applied=r.rule_applied,
                original_personal=_round2(r.original_personal * health_ratio),
                reduced_personal=_round2(r.reduced_personal * health_ratio),
            ) for r in detail_rows],
        )
        health_employee = _round2(reduced_total * health_ratio)
        health_employer = _round2(health_employer * health_ratio)
    else:
        health_employee = _round2(health_total * health_work_ratio * health_ratio)
        health_employer = _round2(health_total * health_emp_ratio * health_ratio)

    health_insurance = ItemBreakdown(
        name="健保",
        employer=health_employer,
        employee=health_employee,
        total=health_employer + health_employee,
    )

    # 職災（全雇主）
    occ_rate = Decimal(str(occ.get("rate", 0.0022)))
    occ_total = _round2(lab_level * occ_rate)
    if use_proration:
        occ_month_total = occupational_accident_month_fee(year, month, enroll_d, cancel_d, occ_total)
        occupational_accident = ItemBreakdown(name="職災", employer=occ_month_total, employee=Decimal("0"), total=occ_month_total)
    else:
        occupational_accident = ItemBreakdown(name="職災", employer=occ_total, employee=Decimal("0"), total=occ_total)

    # 勞退 6%（全雇主）
    pension_ratio = Decimal(str(pension.get("employer_ratio", 0.06)))
    pension_total = _round2(lab_level * pension_ratio)
    if use_proration:
        pension_month_total = labor_pension_month_fee(year, month, enroll_d, cancel_d, pension_total)
        labor_pension = ItemBreakdown(name="勞退6%", employer=pension_month_total, employee=Decimal("0"), total=pension_month_total)
    else:
        labor_pension = ItemBreakdown(name="勞退6%", employer=pension_total, employee=Decimal("0"), total=pension_total)

    # 團保：固定月費（config），不按天數比例，全由員工負擔（不從 Excel/規則表讀取）
    group_monthly = group_insurance_fee if group_insurance_fee is not None else Decimal(str(settings.group_insurance_monthly_fee))
    group_insurance = ItemBreakdown(name="團保", employer=Decimal("0"), employee=group_monthly, total=group_monthly)

    total_employer = (
        labor_insurance.employer
        + health_insurance.employer
        + occupational_accident.employer
        + labor_pension.employer
        + group_insurance.employer
    )
    total_employee = labor_insurance.employee + health_insurance.employee + group_insurance.employee
    total = total_employer + total_employee

    insured_days: Optional[int] = None
    billing_note: Optional[str] = None
    if use_proration and year is not None and month is not None and enroll_d is not None:
        insured_days = get_insured_days_in_month(year, month, enroll_d, cancel_d)
        d_in_month = days_in_month(year, month)
        if insured_days >= d_in_month:
            parts = [f"當月整月在保（{insured_days} 日），勞保/職災/勞退收整月費用"]
        else:
            parts = [f"當月加保 {insured_days} 日，勞保/職災/勞退按 (月費÷30)×{insured_days} 計"]
        parts.append("團保固定月費，全由員工負擔")
        if float(health_ratio) >= 1:
            parts.append("健保當月整月計")
        elif float(health_ratio) == 0:
            parts.append("健保當月不計")
        else:
            parts.append("健保當月按比例計")
        billing_note = "；".join(parts)

    # 計算過程（供前端顯示：如何得出表格上的金額）
    calculation_steps: List[Dict[str, str]] = []
    day_note = ""
    if use_proration and insured_days is not None:
        d_in_m = days_in_month(year, month) if (year and month) else 30
        day_note = f"整月計" if insured_days >= d_in_m else f"按 {insured_days} 天計"
    else:
        day_note = "整月計"
    # 勞保：月額 → 雇主/員工/小計，算式對應表格數字
    lab_amt = labor_insurance.total
    calculation_steps.append({
        "item": "勞保",
        "detail": f"① 月額 = 投保級距 {_fmt(lab_level)} × 費率 {float(lab_rate)*100:.1f}% = {_fmt(lab_total)} 元\n② 當月 {day_note}，當月勞保費 = {_fmt(lab_amt)} 元\n③ 雇主 = {_fmt(lab_amt)} × {float(lab_emp_ratio)*100:.0f}% = {_fmt(labor_insurance.employer)} 元；員工 = {_fmt(lab_amt)} × {float(lab_work_ratio)*100:.0f}% = {_fmt(labor_insurance.employee)} 元 → 小計 {_fmt(labor_insurance.total)} 元",
    })
    calculation_steps.append({
        "item": "職災",
        "detail": f"① 月額 = 投保級距 {_fmt(lab_level)} × 費率 {float(occ_rate)*100:.2f}% = {_fmt(occ_total)} 元\n② 當月 {day_note} → 當月職災費 {_fmt(occupational_accident.total)} 元（全由雇主負擔）",
    })
    calculation_steps.append({
        "item": "勞退6%",
        "detail": f"① 月額 = 投保級距 {_fmt(lab_level)} × 6% = {_fmt(pension_total)} 元\n② 當月 {day_note} → 當月勞退 {_fmt(labor_pension.total)} 元（全由雇主負擔）",
    })
    calculation_steps.append({
        "item": "團保",
        "detail": f"固定月費 {_fmt(group_insurance.total)} 元（全由員工負擔，不按天數比例）",
    })
    calculation_steps.append({
        "item": "健保",
        "detail": f"① 每人月額 = 投保級距 {_fmt(lab_level)} × 費率 {float(health_rate)*100:.2f}% = {_fmt(base_per_person)} 元；計 {health_people} 人 → 月額合計 {_fmt(health_total)} 元\n② 當月整月計 → 雇主 = {_fmt(health_total)} × 60% = {_fmt(health_insurance.employer)} 元；員工 = {_fmt(health_total)} × 30% = {_fmt(health_insurance.employee)} 元 → 小計 {_fmt(health_insurance.total)} 元",
    })

    return InsuranceEstimateResponse(
        insured_salary_level=lab_level,
        labor_insurance=labor_insurance,
        health_insurance=health_insurance,
        health_insurance_breakdown=health_insurance_breakdown,
        occupational_accident=occupational_accident,
        labor_pension=labor_pension,
        group_insurance=group_insurance,
        total_employer=_round2(total_employer),
        total_employee=_round2(total_employee),
        total=_round2(total),
        dependent_count=dep_count,
        insured_days=insured_days,
        billing_note=billing_note,
        calculation_steps=calculation_steps,
    )
