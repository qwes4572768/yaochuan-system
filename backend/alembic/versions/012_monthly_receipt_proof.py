"""每月入帳新增匯款證明欄位 proof_pdf_path

Revision ID: 012
Revises: 011
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(connection, table: str):
    if connection.dialect.name == "sqlite":
        r = connection.execute(sa.text(f"PRAGMA table_info({table})"))
        return {row[1].lower() for row in r}
    return set()


def upgrade() -> None:
    conn = op.get_bind()
    existing = _get_columns(conn, "site_monthly_receipts")
    if "proof_pdf_path" in existing:
        return
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("ALTER TABLE site_monthly_receipts ADD COLUMN proof_pdf_path VARCHAR(500)"))
    else:
        op.add_column("site_monthly_receipts", sa.Column("proof_pdf_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("site_monthly_receipts", "proof_pdf_path")
