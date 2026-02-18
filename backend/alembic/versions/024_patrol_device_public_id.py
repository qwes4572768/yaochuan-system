"""patrol device public id

Revision ID: 024
Revises: 023
Create Date: 2026-02-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.add_column(sa.Column("device_public_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_patrol_devices_device_public_id", ["device_public_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("patrol_devices") as batch_op:
        batch_op.drop_index("ix_patrol_devices_device_public_id")
        batch_op.drop_column("device_public_id")
