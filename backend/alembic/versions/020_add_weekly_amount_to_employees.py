"""add weekly amount for property payroll

Revision ID: 020
Revises: 019
Create Date: 2026-02-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "weekly_amount",
            sa.Numeric(12, 2),
            nullable=True,
            comment="物業每週完成給付金額（僅 WEEKLY_2H 使用）",
        ),
    )
    op.execute(
        """
        UPDATE employees
        SET weekly_amount = property_salary
        WHERE registration_type = 'property'
          AND property_pay_mode = 'WEEKLY_2H'
          AND weekly_amount IS NULL
          AND property_salary IS NOT NULL
          AND property_salary > 0
        """
    )


def downgrade() -> None:
    op.drop_column("employees", "weekly_amount")
