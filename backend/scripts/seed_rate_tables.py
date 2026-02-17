"""Seed 級距表：從 config/rate_tables_seed.json 匯入範例資料（需先執行 alembic upgrade）"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

# 專案根目錄
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import RateTable, RateItem


async def run():
    seed_path = ROOT / "config" / "rate_tables_seed.json"
    if not seed_path.exists():
        print(f"找不到 {seed_path}")
        return
    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tables_data = data.get("tables", [])
    if not tables_data:
        print("tables 為空")
        return

    async with AsyncSessionLocal() as db:
        for pt in tables_data:
            eff_from = date.fromisoformat(pt["effective_from"][:10])
            eff_to = None
            if pt.get("effective_to"):
                eff_to = date.fromisoformat(pt["effective_to"][:10])
            total_rate = Decimal(str(pt["total_rate"])) if pt.get("total_rate") is not None else None
            tbl = RateTable(
                type=pt["type"],
                version=pt.get("version", "2025-01"),
                effective_from=eff_from,
                effective_to=eff_to,
                total_rate=total_rate,
                note=pt.get("note"),
            )
            db.add(tbl)
            await db.flush()
            for it in pt.get("items", []):
                salary_min = Decimal(str(it["salary_min"]))
                salary_max = Decimal(str(it["salary_max"]))
                insured = Decimal(str(it["insured_salary"])) if it.get("insured_salary") is not None else None
                emp_r = Decimal(str(it.get("employee_rate", 0)))
                emp_r_company = Decimal(str(it.get("employer_rate", 0)))
                gov_r = Decimal(str(it["gov_rate"])) if it.get("gov_rate") is not None else None
                fixed = Decimal(str(it["fixed_amount_if_any"])) if it.get("fixed_amount_if_any") is not None else None
                db.add(
                    RateItem(
                        table_id=tbl.id,
                        level_name=it.get("level_name"),
                        salary_min=salary_min,
                        salary_max=salary_max,
                        insured_salary=insured,
                        employee_rate=emp_r,
                        employer_rate=emp_r_company,
                        gov_rate=gov_r,
                        fixed_amount_if_any=fixed,
                    )
                )
            print(f"已建立級距表: {pt['type']} {pt.get('version')} ({eff_from})")
        await db.commit()
    print("Seed 完成。")


if __name__ == "__main__":
    asyncio.run(run())
