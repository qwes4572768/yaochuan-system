"""patrol device password and active state

Revision ID: 023
Revises: 022
Create Date: 2026-02-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("unbound_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_patrol_devices_is_active", ["is_active"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.drop_index("ix_patrol_devices_is_active")
        batch_op.drop_column("unbound_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("password_hash")
