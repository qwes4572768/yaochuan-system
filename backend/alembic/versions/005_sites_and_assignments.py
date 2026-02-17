"""案場管理：sites + site_employee_assignments（案場與員工多對多指派）

Revision ID: 005
Revises: 004
Create Date: 2026-01-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="案場名稱"),
        sa.Column("client_name", sa.String(100), nullable=False, comment="客戶名稱"),
        sa.Column("address", sa.String(500), nullable=False, comment="案場地址"),
        sa.Column("contract_start", sa.Date(), nullable=False, comment="合約起始日"),
        sa.Column("contract_end", sa.Date(), nullable=True, comment="合約結束日"),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False, comment="每月合約金額"),
        sa.Column("payment_method", sa.String(20), nullable=False, comment="收款方式：transfer/現金/支票"),
        sa.Column("receivable_day", sa.Integer(), nullable=False, comment="每月應收日 1-31"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("daily_required_count", sa.Integer(), nullable=True, comment="每日需要人數"),
        sa.Column("shift_hours", sa.Numeric(4, 1), nullable=True, comment="每班別工時，如 8 / 12"),
        sa.Column("is_84_1", sa.Boolean(), nullable=True, server_default="0", comment="是否屬於 84-1 案場"),
        sa.Column("night_shift_allowance", sa.Numeric(10, 2), nullable=True, comment="夜班加給金額"),
        sa.Column("bear_labor_insurance", sa.Boolean(), nullable=True, server_default="1", comment="此案場是否需負擔勞保公司負擔"),
        sa.Column("bear_health_insurance", sa.Boolean(), nullable=True, server_default="1", comment="此案場是否需負擔健保公司負擔"),
        sa.Column("has_group_or_occupational", sa.Boolean(), nullable=True, server_default="0", comment="此案場是否有團保或職災保費"),
        sa.Column("rebate_type", sa.String(20), nullable=True, comment="案場回饋：amount/percent"),
        sa.Column("rebate_value", sa.Numeric(12, 2), nullable=True, comment="回饋金額或百分比數值"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "site_employee_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True, comment="指派生效日（可空表立即生效）"),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="指派迄日（可空表持續）"),
        sa.Column("notes", sa.String(200), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "employee_id", name="uq_site_employee"),
    )
    op.create_index(op.f("ix_site_employee_assignments_site_id"), "site_employee_assignments", ["site_id"], unique=False)
    op.create_index(op.f("ix_site_employee_assignments_employee_id"), "site_employee_assignments", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_site_employee_assignments_employee_id"), table_name="site_employee_assignments")
    op.drop_index(op.f("ix_site_employee_assignments_site_id"), table_name="site_employee_assignments")
    op.drop_table("site_employee_assignments")
    op.drop_table("sites")
