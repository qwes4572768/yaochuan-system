"""patrol 案場分類 site_id：新增欄位、預設案場、回填舊資料

Phase 1：patrol_points 已有 site_id（nullable）。
- patrol_devices / patrol_logs 新增 site_id（nullable）
- 建立預設案場「未分類(舊資料)」
- 回填：site_id IS NULL 的紀錄設為 default_site_id
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SITE_NAME = "未分類(舊資料)"


def upgrade() -> None:
    conn = op.get_bind()

    # 1) patrol_devices 新增 site_id（nullable）
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.add_column(
            sa.Column("site_id", sa.Integer(), nullable=True, comment="案場分類")
        )
        batch_op.create_foreign_key(
            "fk_patrol_devices_site_id_sites",
            "sites",
            ["site_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_patrol_devices_site_id", ["site_id"], unique=False)

    # 2) patrol_logs 新增 site_id（nullable）
    with op.batch_alter_table("patrol_logs") as batch_op:
        batch_op.add_column(
            sa.Column("site_id", sa.Integer(), nullable=True, comment="案場分類（由巡邏點帶入）")
        )
        batch_op.create_foreign_key(
            "fk_patrol_logs_site_id_sites",
            "sites",
            ["site_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_patrol_logs_site_id", ["site_id"], unique=False)

    # 3) 建立預設案場「未分類(舊資料)」（若不存在）
    now = datetime.utcnow()
    contract_start = date(2000, 1, 1)  # 極早日期，避免到期
    # INSERT 僅當尚無此名稱的案場（依 name 判斷）
    if conn.dialect.name == "sqlite":
        conn.execute(
            sa.text("""
                INSERT INTO sites (
                    name, client_name, address, contract_start,
                    monthly_amount, payment_method, receivable_day,
                    created_at, updated_at
                )
                SELECT :name, :client_name, :address, :contract_start,
                       :monthly_amount, :payment_method, :receivable_day,
                       :now, :now
                WHERE NOT EXISTS (SELECT 1 FROM sites WHERE name = :name)
            """),
            {
                "name": DEFAULT_SITE_NAME,
                "client_name": DEFAULT_SITE_NAME,
                "address": "",
                "contract_start": contract_start,
                "monthly_amount": 0,
                "payment_method": "transfer",
                "receivable_day": 1,
                "now": now,
            },
        )
    else:
        conn.execute(
            sa.text("""
                INSERT INTO sites (
                    name, client_name, address, contract_start,
                    monthly_amount, payment_method, receivable_day,
                    created_at, updated_at
                )
                SELECT :name, :client_name, :address, :contract_start,
                       :monthly_amount, :payment_method, :receivable_day,
                       :now, :now
                WHERE NOT EXISTS (SELECT 1 FROM sites WHERE name = :name)
            """),
            {
                "name": DEFAULT_SITE_NAME,
                "client_name": DEFAULT_SITE_NAME,
                "address": "",
                "contract_start": contract_start,
                "monthly_amount": 0,
                "payment_method": "transfer",
                "receivable_day": 1,
                "now": now,
            },
        )

    # 4) 取得預設案場 id
    r = conn.execute(
        sa.text("SELECT id FROM sites WHERE name = :name"),
        {"name": DEFAULT_SITE_NAME},
    )
    row = r.fetchone()
    if not row:
        raise RuntimeError("預設案場「未分類(舊資料)」建立失敗")
    default_site_id = row[0]

    # 5) 回填 patrol_points.site_id
    conn.execute(
        sa.text("UPDATE patrol_points SET site_id = :sid WHERE site_id IS NULL"),
        {"sid": default_site_id},
    )

    # 6) 回填 patrol_devices.site_id
    conn.execute(
        sa.text("UPDATE patrol_devices SET site_id = :sid WHERE site_id IS NULL"),
        {"sid": default_site_id},
    )

    # 7) 回填 patrol_logs.site_id：優先由 point 帶入，無 point 或 point.site_id 空則用 default
    if conn.dialect.name == "sqlite":
        conn.execute(
            sa.text("""
                UPDATE patrol_logs
                SET site_id = COALESCE(
                    (SELECT site_id FROM patrol_points WHERE patrol_points.id = patrol_logs.point_id),
                    :sid
                )
                WHERE site_id IS NULL
            """),
            {"sid": default_site_id},
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE patrol_logs pl
                SET site_id = COALESCE(
                    (SELECT site_id FROM patrol_points pp WHERE pp.id = pl.point_id),
                    :sid
                )
                WHERE pl.site_id IS NULL
            """),
            {"sid": default_site_id},
        )


def downgrade() -> None:
    op.drop_index("ix_patrol_logs_site_id", table_name="patrol_logs")
    with op.batch_alter_table("patrol_logs") as batch_op:
        batch_op.drop_constraint("fk_patrol_logs_site_id_sites", type_="foreignkey")
        batch_op.drop_column("site_id")

    op.drop_index("ix_patrol_devices_site_id", table_name="patrol_devices")
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.drop_constraint("fk_patrol_devices_site_id_sites", type_="foreignkey")
        batch_op.drop_column("site_id")
