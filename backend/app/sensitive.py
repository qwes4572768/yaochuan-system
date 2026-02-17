"""API 回傳前：解密 + 依權限遮罩敏感欄位（national_id、reg_address、live_address）"""
from typing import Any, Dict, List, Optional

from app.crypto import decrypt, mask_id_number, mask_address
from app.models import Employee, Dependent


def _mask_or_plain(
    raw_value: Optional[str],
    reveal: bool,
    mask_fn,
) -> Optional[str]:
    plain = decrypt(raw_value) if raw_value else None
    if not plain:
        return None
    return plain if reveal else mask_fn(plain)


def employee_to_read_dict(emp: Employee, reveal_sensitive: bool = False) -> Dict[str, Any]:
    """將 Employee ORM 轉成 API 回傳用 dict，敏感欄位依 reveal_sensitive 遮罩或明文"""
    deps: List[Dict[str, Any]] = []
    if emp.dependents:
        for d in emp.dependents:
            deps.append(dependent_to_read_dict(d, reveal_sensitive))
    return {
        "id": emp.id,
        "name": emp.name,
        "birth_date": emp.birth_date,
        "national_id": _mask_or_plain(emp.national_id, reveal_sensitive, mask_id_number),
        "reg_address": _mask_or_plain(emp.reg_address, reveal_sensitive, mask_address),
        "live_address": _mask_or_plain(emp.live_address, reveal_sensitive, mask_address),
        "live_same_as_reg": emp.live_same_as_reg,
        "salary_type": emp.salary_type,
        "salary_value": float(emp.salary_value) if emp.salary_value is not None else None,
        "insured_salary_level": float(emp.insured_salary_level) if emp.insured_salary_level is not None else None,
        "enroll_date": emp.enroll_date,
        "cancel_date": emp.cancel_date,
        "dependent_count": emp.dependent_count,
        "pension_self_6": getattr(emp, "pension_self_6", False),
        "registration_type": getattr(emp, "registration_type", "security"),
        "pay_method": getattr(emp, "pay_method", "CASH"),
        "bank_code": getattr(emp, "bank_code", None),
        "branch_code": getattr(emp, "branch_code", None),
        "bank_account": getattr(emp, "bank_account", None),
        "property_pay_mode": getattr(emp, "property_pay_mode", None),
        "security_pay_mode": getattr(emp, "security_pay_mode", None),
        "smith_pay_mode": getattr(emp, "smith_pay_mode", None),
        "lixiang_pay_mode": getattr(emp, "lixiang_pay_mode", None),
        "weekly_amount": float(emp.weekly_amount) if getattr(emp, "weekly_amount", None) is not None else None,
        "property_salary": float(emp.property_salary) if getattr(emp, "property_salary", None) is not None else None,
        "safety_pdf_path": emp.safety_pdf_path,
        "contract_84_1_pdf_path": emp.contract_84_1_pdf_path,
        "notes": emp.notes,
        "created_at": emp.created_at,
        "updated_at": emp.updated_at,
        "dependents": deps,
    }


def dependent_to_read_dict(dep: Dependent, reveal_sensitive: bool = False) -> Dict[str, Any]:
    """將 Dependent ORM 轉成 API 回傳用 dict，身分證依 reveal_sensitive 遮罩或明文"""
    return {
        "id": dep.id,
        "employee_id": dep.employee_id,
        "name": dep.name,
        "birth_date": dep.birth_date,
        "national_id": _mask_or_plain(dep.national_id, reveal_sensitive, mask_id_number),
        "relation": dep.relation,
        "city": dep.city,
        "is_disabled": dep.is_disabled,
        "disability_level": dep.disability_level,
        "notes": dep.notes,
        "created_at": dep.created_at,
        "updated_at": dep.updated_at,
    }


def employee_list_item_dict(emp: Employee, reveal_sensitive: bool = False) -> Dict[str, Any]:
    """列表用：僅部分欄位"""
    return {
        "id": emp.id,
        "name": emp.name,
        "birth_date": emp.birth_date,
        "insured_salary_level": float(emp.insured_salary_level) if emp.insured_salary_level is not None else None,
        "enroll_date": emp.enroll_date,
        "dependent_count": emp.dependent_count,
    }
