"""規則模組 API：健保分攤/減免規則（可擴充、集中於 rules 模組）"""
from typing import Any, List
from fastapi import APIRouter

from app.rules.health_reduction import get_health_reduction_rules

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/health-reduction", response_model=List[dict])
async def list_health_reduction_rules() -> List[dict]:
    """
    取得健保分攤/減免規則（來自 config/health_reduction_rules.yaml）。
    規則集中於 rules 模組，可擴充、不寫死在頁面。
    """
    return get_health_reduction_rules()
