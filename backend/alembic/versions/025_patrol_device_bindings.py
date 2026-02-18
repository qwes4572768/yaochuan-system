"""patrol device bindings table

Revision ID: 025
Revises: 024
Create Date: 2026-02-18
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patrol_device_bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_public_id", sa.String(length=36), nullable=False, comment="裝置永久識別碼 UUID"),
        sa.Column("employee_name", sa.String(length=80), nullable=True, comment="員工姓名"),
        sa.Column("site_name", sa.String(length=120), nullable=True, comment="案場名稱"),
        sa.Column("password_hash", sa.String(length=255), nullable=True, comment="綁定密碼雜湊值"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否仍為有效綁定"),
        sa.Column("bound_at", sa.DateTime(), nullable=True, comment="綁定時間"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True, comment="最後登入/使用時間"),
        sa.Column("device_info", sa.JSON(), nullable=True, comment="設備資訊 JSON（ua/platform/lang/screen/tz）"),
        sa.Column("user_agent", sa.String(length=600), nullable=True, comment="UA"),
        sa.Column("platform", sa.String(length=120), nullable=True, comment="平台"),
        sa.Column("browser", sa.String(length=120), nullable=True, comment="瀏覽器"),
        sa.Column("language", sa.String(length=30), nullable=True, comment="語言"),
        sa.Column("screen_size", sa.String(length=40), nullable=True, comment="螢幕尺寸"),
        sa.Column("timezone", sa.String(length=80), nullable=True, comment="時區"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_public_id"),
    )
    op.create_index(op.f("ix_patrol_device_bindings_device_public_id"), "patrol_device_bindings", ["device_public_id"], unique=True)
    op.create_index(op.f("ix_patrol_device_bindings_employee_name"), "patrol_device_bindings", ["employee_name"], unique=False)
    op.create_index(op.f("ix_patrol_device_bindings_site_name"), "patrol_device_bindings", ["site_name"], unique=False)
    op.create_index(op.f("ix_patrol_device_bindings_is_active"), "patrol_device_bindings", ["is_active"], unique=False)
    op.create_index(op.f("ix_patrol_device_bindings_bound_at"), "patrol_device_bindings", ["bound_at"], unique=False)
    op.create_index(op.f("ix_patrol_device_bindings_last_seen_at"), "patrol_device_bindings", ["last_seen_at"], unique=False)

    # Backfill：將既有 patrol_devices 的有效永久裝置同步進新表，避免升級後入口顯示未綁定。
    op.execute(
        """
        INSERT INTO patrol_device_bindings (
            device_public_id,
            employee_name,
            site_name,
            password_hash,
            is_active,
            bound_at,
            last_seen_at,
            user_agent,
            platform,
            browser,
            language,
            screen_size,
            timezone,
            created_at,
            updated_at
        )
        SELECT
            d.device_public_id,
            d.employee_name,
            d.site_name,
            d.password_hash,
            d.is_active,
            d.bound_at,
            d.bound_at,
            d.user_agent,
            d.platform,
            d.browser,
            d.language,
            d.screen_size,
            d.timezone,
            d.created_at,
            d.created_at
        FROM patrol_devices d
        WHERE d.device_public_id IS NOT NULL
          AND d.device_public_id <> ''
          AND d.id = (
              SELECT MAX(d2.id)
              FROM patrol_devices d2
              WHERE d2.device_public_id = d.device_public_id
          )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_patrol_device_bindings_last_seen_at"), table_name="patrol_device_bindings")
    op.drop_index(op.f("ix_patrol_device_bindings_bound_at"), table_name="patrol_device_bindings")
    op.drop_index(op.f("ix_patrol_device_bindings_is_active"), table_name="patrol_device_bindings")
    op.drop_index(op.f("ix_patrol_device_bindings_site_name"), table_name="patrol_device_bindings")
    op.drop_index(op.f("ix_patrol_device_bindings_employee_name"), table_name="patrol_device_bindings")
    op.drop_index(op.f("ix_patrol_device_bindings_device_public_id"), table_name="patrol_device_bindings")
    op.drop_table("patrol_device_bindings")
