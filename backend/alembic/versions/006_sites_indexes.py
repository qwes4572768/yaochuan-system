"""案場表與指派表索引：sites 常用查詢欄位、assignments 期間查詢；刪除策略維持 CASCADE。

Revision ID: 006
Revises: 005
Create Date: 2026-01-30

"""
from typing import Sequence, Union
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sites 常用查詢：name、client_name、contract_end、payment_method
    op.create_index(op.f("ix_sites_name"), "sites", ["name"], unique=False)
    op.create_index(op.f("ix_sites_client_name"), "sites", ["client_name"], unique=False)
    op.create_index(op.f("ix_sites_contract_end"), "sites", ["contract_end"], unique=False)
    op.create_index(op.f("ix_sites_payment_method"), "sites", ["payment_method"], unique=False)

    # site_employee_assignments：site_id、employee_id 已有 FK 索引；補 effective_from、effective_to
    op.create_index(op.f("ix_site_employee_assignments_effective_from"), "site_employee_assignments", ["effective_from"], unique=False)
    op.create_index(op.f("ix_site_employee_assignments_effective_to"), "site_employee_assignments", ["effective_to"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_site_employee_assignments_effective_to"), table_name="site_employee_assignments")
    op.drop_index(op.f("ix_site_employee_assignments_effective_from"), table_name="site_employee_assignments")
    op.drop_index(op.f("ix_sites_payment_method"), table_name="sites")
    op.drop_index(op.f("ix_sites_contract_end"), table_name="sites")
    op.drop_index(op.f("ix_sites_client_name"), table_name="sites")
    op.drop_index(op.f("ix_sites_name"), table_name="sites")
