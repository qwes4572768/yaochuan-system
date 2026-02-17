"""patrol 管理：綁定碼、設備、巡邏點、巡邏紀錄

Revision ID: 017
Revises: 016
Create Date: 2026-02-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patrol_binding_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False, comment="綁定碼"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="到期時間"),
        sa.Column("used_at", sa.DateTime(), nullable=True, comment="使用時間（一次性）"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patrol_binding_codes_code"), "patrol_binding_codes", ["code"], unique=True)
    op.create_index(op.f("ix_patrol_binding_codes_expires_at"), "patrol_binding_codes", ["expires_at"], unique=False)

    op.create_table(
        "patrol_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("binding_code_id", sa.Integer(), nullable=True),
        sa.Column("device_token", sa.String(length=140), nullable=False, comment="伺服器簽發設備 token"),
        sa.Column("employee_name", sa.String(length=80), nullable=False, comment="員工姓名"),
        sa.Column("site_name", sa.String(length=120), nullable=False, comment="案場名稱"),
        sa.Column("device_fingerprint", sa.Text(), nullable=True, comment="前端回傳設備指紋 JSON"),
        sa.Column("user_agent", sa.String(length=600), nullable=True),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("browser", sa.String(length=120), nullable=True),
        sa.Column("language", sa.String(length=30), nullable=True),
        sa.Column("screen_size", sa.String(length=40), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("bound_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["binding_code_id"], ["patrol_binding_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patrol_devices_binding_code_id"), "patrol_devices", ["binding_code_id"], unique=False)
    op.create_index(op.f("ix_patrol_devices_bound_at"), "patrol_devices", ["bound_at"], unique=False)
    op.create_index(op.f("ix_patrol_devices_device_token"), "patrol_devices", ["device_token"], unique=True)
    op.create_index(op.f("ix_patrol_devices_employee_name"), "patrol_devices", ["employee_name"], unique=False)
    op.create_index(op.f("ix_patrol_devices_site_name"), "patrol_devices", ["site_name"], unique=False)

    op.create_table(
        "patrol_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("point_code", sa.String(length=80), nullable=False, comment="巡邏點編號"),
        sa.Column("point_name", sa.String(length=120), nullable=False, comment="巡邏點名稱"),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("site_name", sa.String(length=120), nullable=True, comment="案場名稱（快照）"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patrol_points_point_code"), "patrol_points", ["point_code"], unique=True)
    op.create_index(op.f("ix_patrol_points_site_id"), "patrol_points", ["site_id"], unique=False)
    op.create_index(op.f("ix_patrol_points_site_name"), "patrol_points", ["site_name"], unique=False)

    op.create_table(
        "patrol_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("point_id", sa.Integer(), nullable=True),
        sa.Column("employee_name", sa.String(length=80), nullable=False),
        sa.Column("site_name", sa.String(length=120), nullable=False),
        sa.Column("point_code", sa.String(length=80), nullable=False),
        sa.Column("point_name", sa.String(length=120), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("checkin_time", sa.Time(), nullable=False),
        sa.Column("checkin_ampm", sa.String(length=10), nullable=False),
        sa.Column("qr_value", sa.String(length=1000), nullable=True),
        sa.Column("device_info", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["patrol_devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["point_id"], ["patrol_points.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patrol_logs_device_id"), "patrol_logs", ["device_id"], unique=False)
    op.create_index(op.f("ix_patrol_logs_point_id"), "patrol_logs", ["point_id"], unique=False)
    op.create_index(op.f("ix_patrol_logs_employee_name"), "patrol_logs", ["employee_name"], unique=False)
    op.create_index(op.f("ix_patrol_logs_site_name"), "patrol_logs", ["site_name"], unique=False)
    op.create_index(op.f("ix_patrol_logs_point_code"), "patrol_logs", ["point_code"], unique=False)
    op.create_index(op.f("ix_patrol_logs_checkin_date"), "patrol_logs", ["checkin_date"], unique=False)
    op.create_index(op.f("ix_patrol_logs_created_at"), "patrol_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_patrol_logs_created_at"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_checkin_date"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_point_code"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_site_name"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_employee_name"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_point_id"), table_name="patrol_logs")
    op.drop_index(op.f("ix_patrol_logs_device_id"), table_name="patrol_logs")
    op.drop_table("patrol_logs")

    op.drop_index(op.f("ix_patrol_points_site_name"), table_name="patrol_points")
    op.drop_index(op.f("ix_patrol_points_site_id"), table_name="patrol_points")
    op.drop_index(op.f("ix_patrol_points_point_code"), table_name="patrol_points")
    op.drop_table("patrol_points")

    op.drop_index(op.f("ix_patrol_devices_site_name"), table_name="patrol_devices")
    op.drop_index(op.f("ix_patrol_devices_employee_name"), table_name="patrol_devices")
    op.drop_index(op.f("ix_patrol_devices_device_token"), table_name="patrol_devices")
    op.drop_index(op.f("ix_patrol_devices_bound_at"), table_name="patrol_devices")
    op.drop_index(op.f("ix_patrol_devices_binding_code_id"), table_name="patrol_devices")
    op.drop_table("patrol_devices")

    op.drop_index(op.f("ix_patrol_binding_codes_expires_at"), table_name="patrol_binding_codes")
    op.drop_index(op.f("ix_patrol_binding_codes_code"), table_name="patrol_binding_codes")
    op.drop_table("patrol_binding_codes")
