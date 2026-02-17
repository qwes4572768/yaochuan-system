"""salary_profiles + insurance_monthly_results：薪資可擴充、保險結果落表供會計

Revision ID: 004
Revises: 003
Create Date: 2025-01-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salary_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("salary_type", sa.String(20), nullable=False),
        sa.Column("monthly_base", sa.Numeric(12, 2), nullable=True),
        sa.Column("daily_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("overtime_eligible", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("calculation_rules", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", name="uq_salary_profiles_employee_id"),
    )
    op.create_index(op.f("ix_salary_profiles_employee_id"), "salary_profiles", ["employee_id"], unique=True)

    op.create_table(
        "insurance_monthly_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("year_month", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("employee_amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("employer_amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("gov_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_insurance_monthly_results_employee_id"), "insurance_monthly_results", ["employee_id"], unique=False)
    op.create_index(op.f("ix_insurance_monthly_results_year_month"), "insurance_monthly_results", ["year_month"], unique=False)
    op.create_index(op.f("ix_insurance_monthly_results_item_type"), "insurance_monthly_results", ["item_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_insurance_monthly_results_item_type"), table_name="insurance_monthly_results")
    op.drop_index(op.f("ix_insurance_monthly_results_year_month"), table_name="insurance_monthly_results")
    op.drop_index(op.f("ix_insurance_monthly_results_employee_id"), table_name="insurance_monthly_results")
    op.drop_table("insurance_monthly_results")
    op.drop_index(op.f("ix_salary_profiles_employee_id"), table_name="salary_profiles")
    op.drop_table("salary_profiles")
