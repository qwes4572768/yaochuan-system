"""案場歷史：sites 新增 is_archived, archived_at, archived_reason（到期未續約歸檔）

Revision ID: 011
Revises: 010
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
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
        op.add_column("sites", sa.Column("is_archived", sa.Boolean(), nullable=True, server_default="0"))
        op.add_column("sites", sa.Column("archived_at", sa.DateTime(), nullable=True))
        op.add_column("sites", sa.Column("archived_reason", sa.String(50), nullable=True))
        return
    existing = _get_sites_columns(connection)
    if "is_archived" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
    if "archived_at" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN archived_at DATETIME"))
    if "archived_reason" not in existing:
        connection.execute(sa.text("ALTER TABLE sites ADD COLUMN archived_reason VARCHAR(50)"))
    connection.execute(sa.text("UPDATE sites SET is_archived = 0 WHERE is_archived IS NULL"))


def downgrade() -> None:
    op.drop_column("sites", "archived_reason")
    op.drop_column("sites", "archived_at")
    op.drop_column("sites", "is_archived")
