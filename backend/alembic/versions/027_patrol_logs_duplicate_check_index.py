"""patrol_logs 防重複掃碼查詢索引

Revision ID: 027
Revises: 026
Create Date: 2026-02-18

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 設備打點：查詢 (device_id, point_id) 最近一筆
    op.create_index(
        "ix_patrol_logs_device_point_created",
        "patrol_logs",
        ["device_id", "point_id", "created_at"],
        unique=False,
    )
    # 公開打卡（員工）：查詢 (employee_id, point_id) 最近一筆
    op.create_index(
        "ix_patrol_logs_employee_point_created",
        "patrol_logs",
        ["employee_id", "point_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patrol_logs_employee_point_created", table_name="patrol_logs")
    op.drop_index("ix_patrol_logs_device_point_created", table_name="patrol_logs")
