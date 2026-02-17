"""案場管理擴充：sites 新欄位 + site_contract_files, site_rebates, site_monthly_receipts

Revision ID: 008
Revises: 007
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- sites 新增欄位（保留既有欄位供排班/指派相容） -----
    op.add_column("sites", sa.Column("site_type", sa.String(20), nullable=True, comment="community/factory"))
    op.add_column("sites", sa.Column("service_types", sa.Text(), nullable=True, comment="JSON 多選：駐衛保全/公寓大廈管理/保全綜合"))
    op.add_column("sites", sa.Column("monthly_fee_excl_tax", sa.Numeric(12, 2), nullable=True, comment="月服務費未稅"))
    op.add_column("sites", sa.Column("tax_rate", sa.Numeric(5, 4), nullable=True, comment="稅率 如 0.05"))
    op.add_column("sites", sa.Column("monthly_fee_incl_tax", sa.Numeric(12, 2), nullable=True, comment="月服務費含稅"))
    op.add_column("sites", sa.Column("invoice_due_day", sa.Integer(), nullable=True, comment="每月發票期限日 1-31"))
    op.add_column("sites", sa.Column("payment_due_day", sa.Integer(), nullable=True, comment="每月收款期限日 1-31"))
    op.add_column("sites", sa.Column("remind_days", sa.Integer(), nullable=True, comment="契約到期提醒天數 預設30"))
    op.add_column("sites", sa.Column("customer_name", sa.String(100), nullable=True, comment="客戶名稱"))
    op.add_column("sites", sa.Column("customer_tax_id", sa.String(20), nullable=True, comment="統一編號"))
    op.add_column("sites", sa.Column("customer_contact", sa.String(50), nullable=True, comment="聯絡人"))
    op.add_column("sites", sa.Column("customer_phone", sa.String(50), nullable=True, comment="電話"))
    op.add_column("sites", sa.Column("customer_email", sa.String(100), nullable=True, comment="Email"))
    op.add_column("sites", sa.Column("invoice_title", sa.String(200), nullable=True, comment="發票抬頭"))
    op.add_column("sites", sa.Column("invoice_mail_address", sa.String(500), nullable=True, comment="發票郵寄地址"))
    op.add_column("sites", sa.Column("invoice_receiver", sa.String(100), nullable=True, comment="收件人"))

    # ----- site_contract_files -----
    op.create_table(
        "site_contract_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_site_contract_files_site_id"), "site_contract_files", ["site_id"], unique=False)

    # ----- site_rebates -----
    op.create_table(
        "site_rebates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("cost_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("receipt_pdf_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_site_rebates_site_id"), "site_rebates", ["site_id"], unique=False)

    # ----- site_monthly_receipts -----
    op.create_table(
        "site_monthly_receipts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("billing_month", sa.String(7), nullable=False, comment="YYYY-MM"),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_received", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("received_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_method", sa.String(20), nullable=True, comment="transfer/cash/check/other"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "billing_month", name="uq_site_billing_month"),
    )
    op.create_index(op.f("ix_site_monthly_receipts_site_id"), "site_monthly_receipts", ["site_id"], unique=False)
    op.create_index(op.f("ix_site_monthly_receipts_billing_month"), "site_monthly_receipts", ["billing_month"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_site_monthly_receipts_billing_month"), table_name="site_monthly_receipts")
    op.drop_index(op.f("ix_site_monthly_receipts_site_id"), table_name="site_monthly_receipts")
    op.drop_table("site_monthly_receipts")
    op.drop_index(op.f("ix_site_rebates_site_id"), table_name="site_rebates")
    op.drop_table("site_rebates")
    op.drop_index(op.f("ix_site_contract_files_site_id"), table_name="site_contract_files")
    op.drop_table("site_contract_files")
    for col in (
        "invoice_receiver", "invoice_mail_address", "invoice_title", "customer_email", "customer_phone",
        "customer_contact", "customer_tax_id", "customer_name", "remind_days", "payment_due_day", "invoice_due_day",
        "monthly_fee_incl_tax", "tax_rate", "monthly_fee_excl_tax", "service_types", "site_type",
    ):
        op.drop_column("sites", col)
