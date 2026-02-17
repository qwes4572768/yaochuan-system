"""SQLite 安全升級：sites 缺欄則補（不刪資料），三張表若不存在則建立。
可重複執行（idempotent），適用於從未跑過 008 或 008 只跑一半的狀況。

Revision ID: 009
Revises: 008
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# sites 要補的欄位（008 新增的；contract_start/contract_end 已在 005 故不列）
SITES_ADD_COLUMNS = [
    ("site_type", "TEXT", None),
    ("service_types", "TEXT", None),
    ("monthly_fee_excl_tax", "NUMERIC(12,2)", None),
    ("tax_rate", "NUMERIC(5,4)", "0.05"),
    ("monthly_fee_incl_tax", "NUMERIC(12,2)", None),
    ("invoice_due_day", "INTEGER", None),
    ("payment_due_day", "INTEGER", None),
    ("remind_days", "INTEGER", "30"),
    ("customer_name", "TEXT", None),
    ("customer_tax_id", "TEXT", None),
    ("customer_contact", "TEXT", None),
    ("customer_phone", "TEXT", None),
    ("customer_email", "TEXT", None),
    ("invoice_title", "TEXT", None),
    ("invoice_mail_address", "TEXT", None),
    ("invoice_receiver", "TEXT", None),
]


def _get_sites_columns(connection):
    """回傳 sites 表現有欄位名稱集合（小寫）。"""
    if connection.dialect.name == "sqlite":
        r = connection.execute(sa.text("PRAGMA table_info(sites)"))
        return {row[1].lower() for row in r}
    return set()


def _table_exists(connection, name: str) -> bool:
    if connection.dialect.name == "sqlite":
        r = connection.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": name},
        )
        return r.fetchone() is not None
    return False


def upgrade() -> None:
    connection = op.get_bind()
    existing = _get_sites_columns(connection)

    for col_name, col_type, default in SITES_ADD_COLUMNS:
        if col_name.lower() in existing:
            continue
        default_clause = f" DEFAULT {default}" if default is not None else ""
        sql = f"ALTER TABLE sites ADD COLUMN {col_name} {col_type}{default_clause}"
        connection.execute(sa.text(sql))

    # 三張表若不存在則建立（與 008 結構一致）
    if connection.dialect.name == "sqlite":
        if not _table_exists(connection, "site_contract_files"):
            connection.execute(sa.text("""
                CREATE TABLE site_contract_files (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    uploaded_at DATETIME
                )
            """))
            connection.execute(sa.text("CREATE INDEX ix_site_contract_files_site_id ON site_contract_files (site_id)"))

        if not _table_exists(connection, "site_rebates"):
            connection.execute(sa.text("""
                CREATE TABLE site_rebates (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    item_name VARCHAR(200) NOT NULL,
                    is_completed BOOLEAN DEFAULT 0,
                    completed_date DATE,
                    cost_amount NUMERIC(12,2),
                    receipt_pdf_path VARCHAR(500),
                    notes TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """))
            connection.execute(sa.text("CREATE INDEX ix_site_rebates_site_id ON site_rebates (site_id)"))

        if not _table_exists(connection, "site_monthly_receipts"):
            connection.execute(sa.text("""
                CREATE TABLE site_monthly_receipts (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
                    billing_month VARCHAR(7) NOT NULL,
                    expected_amount NUMERIC(12,2),
                    is_received BOOLEAN DEFAULT 0,
                    received_date DATE,
                    received_amount NUMERIC(12,2),
                    payment_method VARCHAR(20),
                    notes TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    UNIQUE (site_id, billing_month)
                )
            """))
            connection.execute(sa.text("CREATE INDEX ix_site_monthly_receipts_site_id ON site_monthly_receipts (site_id)"))
            connection.execute(sa.text("CREATE INDEX ix_site_monthly_receipts_billing_month ON site_monthly_receipts (billing_month)"))


def downgrade() -> None:
    # 009 為「補欄」用，downgrade 不刪欄位，避免誤刪資料；若需還原請依 008 的 downgrade 手動處理
    pass
