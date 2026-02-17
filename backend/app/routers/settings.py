"""後台設定：勞健保級距/費率/政府補助 - 可更新設定表"""
import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import crud
from app.crud import INSURANCE_KEYS

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/insurance", response_model=Dict[str, Any])
async def get_insurance_settings(db: AsyncSession = Depends(get_db)):
    """
    取得勞健保/職災/團保/勞退 費率與級距設定（供試算與後台維護）。
    若 DB 無設定則回傳 YAML 預設值。
    """
    return await crud.get_all_insurance_rules(db)


@router.put("/insurance")
async def update_insurance_settings(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    更新費率設定表。body 可含：labor_insurance, health_insurance,
    occupational_accident, labor_pension, group_insurance（各為物件）。
    僅更新有傳的 key，未傳的保留原值。
    """
    for key in body:
        if key not in INSURANCE_KEYS:
            raise HTTPException(status_code=400, detail=f"不支援的設定鍵: {key}，僅支援: {list(INSURANCE_KEYS)}")
    for key in INSURANCE_KEYS:
        if key not in body:
            continue
        val = body[key]
        if not isinstance(val, dict):
            raise HTTPException(status_code=400, detail=f"{key} 須為 JSON 物件")
        await crud.set_insurance_config(db, key, json.dumps(val, ensure_ascii=False), description=f"{key} 費率/級距")
    return await crud.get_all_insurance_rules(db)
