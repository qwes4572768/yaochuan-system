"""add company pay mode columns

Revision ID: 021_add_company_pay_modes
Revises: 020_add_weekly_amount_to_employees
Create Date: 2026-02-15 11:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "021_add_company_pay_modes"
down_revision = "020_add_weekly_amount_to_employees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("security_pay_mode", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("smith_pay_mode", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("lixiang_pay_mode", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_column("lixiang_pay_mode")
        batch_op.drop_column("smith_pay_mode")
        batch_op.drop_column("security_pay_mode")
