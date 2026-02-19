"""patrol_points.site_id 改為 NOT NULL（Phase 2）

執行前提：028 回填已完成，且線上運行正常。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patrol_points") as batch_op:
        batch_op.alter_column(
            "site_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("patrol_points") as batch_op:
        batch_op.alter_column(
            "site_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
