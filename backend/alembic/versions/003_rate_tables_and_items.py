"""rate_tables + rate_items：費率/級距表與明細，依類型與生效區間

Revision ID: 003
Revises: 002
Create Date: 2025-01-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_tables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(40), nullable=False, comment="labor_insurance / health_insurance / occupational_accident / labor_pension"),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("total_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rate_tables_type"), "rate_tables", ["type"], unique=False)

    op.create_table(
        "rate_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("level_name", sa.String(30), nullable=True),
        sa.Column("salary_min", sa.Numeric(12, 0), nullable=False),
        sa.Column("salary_max", sa.Numeric(12, 0), nullable=False),
        sa.Column("insured_salary", sa.Numeric(12, 0), nullable=True),
        sa.Column("employee_rate", sa.Numeric(8, 4), nullable=True, server_default="0"),
        sa.Column("employer_rate", sa.Numeric(8, 4), nullable=True, server_default="0"),
        sa.Column("gov_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("fixed_amount_if_any", sa.Numeric(12, 2), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["rate_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rate_items_table_id"), "rate_items", ["table_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rate_items_table_id"), table_name="rate_items")
    op.drop_table("rate_items")
    op.drop_index(op.f("ix_rate_tables_type"), table_name="rate_tables")
    op.drop_table("rate_tables")
