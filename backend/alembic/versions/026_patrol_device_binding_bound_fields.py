"""patrol device binding bound fields

Revision ID: 026
Revises: 025
Create Date: 2026-02-18
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patrol_device_bindings") as batch_op:
        batch_op.add_column(sa.Column("device_fingerprint_json", sa.Text(), nullable=True, comment="設備指紋 JSON（排序後字串）"))
        batch_op.add_column(sa.Column("is_bound", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已完成綁定"))
        batch_op.create_index("ix_patrol_device_bindings_is_bound", ["is_bound"], unique=False)

    op.execute("UPDATE patrol_device_bindings SET is_bound = CASE WHEN is_active THEN 1 ELSE 0 END")


def downgrade() -> None:
    with op.batch_alter_table("patrol_device_bindings") as batch_op:
        batch_op.drop_index("ix_patrol_device_bindings_is_bound")
        batch_op.drop_column("is_bound")
        batch_op.drop_column("device_fingerprint_json")
