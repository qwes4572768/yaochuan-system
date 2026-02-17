"""add employee property payroll fields

Revision ID: 018
Revises: 017
Create Date: 2026-02-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "property_pay_mode",
            sa.String(length=30),
            nullable=True,
            comment="物業計薪模式：WEEKLY_2H / MONTHLY_8H_HOLIDAY",
        ),
    )
    op.add_column(
        "employees",
        sa.Column(
            "property_salary",
            sa.Numeric(12, 2),
            nullable=True,
            comment="物業固定月薪（僅 payroll_type=property 使用）",
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "property_salary")
    op.drop_column("employees", "property_pay_mode")
