"""employees.pension_self_6：員工自提6%勾選（試算/結算帶入）

Revision ID: 014
Revises: 013
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("pension_self_6", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="員工自提6%"),
    )


def downgrade() -> None:
    op.drop_column("employees", "pension_self_6")
