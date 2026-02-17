"""backfill property salary and mode from legacy fields

Revision ID: 019
Revises: 018
Create Date: 2026-02-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 既有物業資料相容：若尚未填 property_salary，沿用舊 salary_value 一次性回填。
    op.execute(
        """
        UPDATE employees
        SET property_salary = salary_value
        WHERE registration_type = 'property'
          AND property_salary IS NULL
          AND salary_value IS NOT NULL
          AND salary_value > 0
        """
    )
    # 舊資料沒有模式時預設 WEEKLY_2H，避免整批回傳 0。
    op.execute(
        """
        UPDATE employees
        SET property_pay_mode = 'WEEKLY_2H'
        WHERE registration_type = 'property'
          AND (property_pay_mode IS NULL OR TRIM(property_pay_mode) = '')
        """
    )


def downgrade() -> None:
    # 僅回退本 migration 填入的預設模式；薪資回填不做反向覆蓋以避免資料遺失。
    op.execute(
        """
        UPDATE employees
        SET property_pay_mode = NULL
        WHERE registration_type = 'property'
          AND property_pay_mode = 'WEEKLY_2H'
        """
    )
