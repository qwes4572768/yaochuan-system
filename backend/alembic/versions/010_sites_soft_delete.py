"""案場軟刪除：sites 新增 is_active, deactivated_at, deactivated_reason

Revision ID: 010
Revises: 009
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_sites_columns(connection):
    if connection.dialect.name == "sqlite":
        r = connection.execute(sa.text("PRAGMA table_info(sites)"))
        return {row[1].lower() for row in r}
    return set()


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        op.add_column("sites", sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"))
        op.add_column("sites", sa.Column("deactivated_at", sa.DateTime(), nullable=True))
        op.add_column("sites", sa.Column("deactivated_reason", sa.String(50), nullable=True))
        return
    existing = _get_sites_columns(connection)
    if "is_active" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN is_active BOOLEAN DEFAULT 1"))
    if "deactivated_at" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN deactivated_at DATETIME"))
    if "deactivated_reason" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN deactivated_reason VARCHAR(50)"))
    connection.execute(sa.text("UPDATE sites SET is_active = 1 WHERE is_active IS NULL"))


def downgrade() -> None:
    op.drop_column("sites", "deactivated_reason")
    op.drop_column("sites", "deactivated_at")
    op.drop_column("sites", "is_active")
