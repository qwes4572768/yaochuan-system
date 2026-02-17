"""Seed 3 筆案場供 list_sites 分頁與 contract_active 驗證（q=驗證 可篩出 3 筆，contract_end 皆已過期）。"""
import asyncio
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import AsyncSessionLocal
from app.models import Site


async def run():
    # 3 筆名稱皆含「驗證」，q=驗證 可篩出 3 筆；contract_end 皆設為過去，contract_active=false 會回傳這 3 筆
    ended = date(2020, 1, 1)
    data = [
        {"name": "驗證案場1", "client_name": "驗證客戶", "address": "台北市", "contract_start": date(2019, 1, 1), "contract_end": ended, "monthly_amount": Decimal("100000"), "payment_method": "transfer", "receivable_day": 5},
        {"name": "驗證案場2", "client_name": "驗證客戶", "address": "新北市", "contract_start": date(2019, 1, 1), "contract_end": ended, "monthly_amount": Decimal("100000"), "payment_method": "transfer", "receivable_day": 5},
        {"name": "驗證案場3", "client_name": "驗證客戶", "address": "桃園市", "contract_start": date(2019, 1, 1), "contract_end": ended, "monthly_amount": Decimal("100000"), "payment_method": "transfer", "receivable_day": 5},
    ]
    async with AsyncSessionLocal() as db:
        for d in data:
            s = Site(**d)
            db.add(s)
        await db.commit()
    print("已新增 3 筆案場（名稱含「驗證」，contract_end=2020-01-01）。請用 GET /api/sites?page=1&page_size=2&q=驗證 等驗證。")


if __name__ == "__main__":
    asyncio.run(run())
