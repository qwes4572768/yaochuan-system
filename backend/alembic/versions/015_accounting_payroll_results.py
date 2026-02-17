"""accounting_payroll_results：傻瓜會計薪資計算結果（year, month, type）

Revision ID: 015
Revises: 014
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_payroll_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False, comment="西元年"),
        sa.Column("month", sa.Integer(), nullable=False, comment="1～12"),
        sa.Column("type", sa.String(30), nullable=False, comment="security / property / smith / cleaning"),
        sa.Column("site", sa.String(100), nullable=False, comment="案場名稱"),
        sa.Column("employee", sa.String(50), nullable=False, comment="員工姓名"),
        sa.Column("total_hours", sa.Float(), nullable=False, comment="總工時"),
        sa.Column("total_salary", sa.Float(), nullable=False, comment="總薪資"),
        sa.Column("status", sa.String(20), nullable=False, comment="滿班/未滿班"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounting_payroll_results_year"), "accounting_payroll_results", ["year"], unique=False)
    op.create_index(op.f("ix_accounting_payroll_results_month"), "accounting_payroll_results", ["month"], unique=False)
    op.create_index(op.f("ix_accounting_payroll_results_type"), "accounting_payroll_results", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_accounting_payroll_results_type"), table_name="accounting_payroll_results")
    op.drop_index(op.f("ix_accounting_payroll_results_month"), table_name="accounting_payroll_results")
    op.drop_index(op.f("ix_accounting_payroll_results_year"), table_name="accounting_payroll_results")
    op.drop_table("accounting_payroll_results")
