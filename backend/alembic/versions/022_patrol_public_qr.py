"""patrol points public_id + fixed QR checkin

Revision ID: 022
Revises: 021
Create Date: 2026-02-14
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patrol_points") as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("location", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM patrol_points WHERE public_id IS NULL OR public_id = ''")).fetchall()
    for row in rows:
        conn.execute(
            sa.text("UPDATE patrol_points SET public_id = :public_id WHERE id = :id"),
            {"public_id": str(uuid.uuid4()), "id": row[0]},
        )

    with op.batch_alter_table("patrol_points") as batch_op:
        batch_op.alter_column("public_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index("ix_patrol_points_public_id", ["public_id"], unique=True)

    with op.batch_alter_table("patrol_logs") as batch_op:
        batch_op.add_column(sa.Column("employee_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_patrol_logs_employee_id_employees",
            "employees",
            ["employee_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_patrol_logs_employee_id", ["employee_id"], unique=False)
        batch_op.alter_column("device_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("patrol_logs") as batch_op:
        batch_op.alter_column("device_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_index("ix_patrol_logs_employee_id")
        batch_op.drop_constraint("fk_patrol_logs_employee_id_employees", type_="foreignkey")
        batch_op.drop_column("employee_id")

    with op.batch_alter_table("patrol_points") as batch_op:
        batch_op.drop_index("ix_patrol_points_public_id")
        batch_op.drop_column("is_active")
        batch_op.drop_column("location")
        batch_op.drop_column("public_id")
