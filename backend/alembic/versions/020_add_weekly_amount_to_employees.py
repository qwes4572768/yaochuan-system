"""add weekly amount for property payroll (補鏈用)

Revision ID: 020_add_weekly_amount_to_employees
Revises: 019
Create Date: 2026-02-16
"""
from __future__ import annotations

from typing import Sequence, Union

revision: str = "020_add_weekly_amount_to_employees"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
