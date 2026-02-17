"""salary_profiles 團保欄位；accounting_payroll_results 擴充扣款與實發欄位

Revision ID: 016
Revises: 015
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "salary_profiles",
        sa.Column("group_insurance_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "salary_profiles",
        sa.Column("group_insurance_fee", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column("accounting_payroll_results", sa.Column("pay_type", sa.String(20), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("gross_salary", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("labor_insurance_employee", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("health_insurance_employee", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("group_insurance", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("self_pension_6", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("deductions_total", sa.Float(), nullable=True))
    op.add_column("accounting_payroll_results", sa.Column("net_salary", sa.Float(), nullable=True))
    op.alter_column(
        "accounting_payroll_results",
        "status",
        existing_type=sa.String(20),
        type_=sa.String(30),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "accounting_payroll_results",
        "status",
        existing_type=sa.String(30),
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.drop_column("accounting_payroll_results", "net_salary")
    op.drop_column("accounting_payroll_results", "deductions_total")
    op.drop_column("accounting_payroll_results", "self_pension_6")
    op.drop_column("accounting_payroll_results", "group_insurance")
    op.drop_column("accounting_payroll_results", "health_insurance_employee")
    op.drop_column("accounting_payroll_results", "labor_insurance_employee")
    op.drop_column("accounting_payroll_results", "gross_salary")
    op.drop_column("accounting_payroll_results", "pay_type")
    op.drop_column("salary_profiles", "group_insurance_fee")
    op.drop_column("salary_profiles", "group_insurance_enabled")
