"""排班 P0：schedules / schedule_shifts / schedule_assignments

Revision ID: 007
Revises: 006
Create Date: 2026-01-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False, comment="案場 ID"),
        sa.Column("year", sa.Integer(), nullable=False, comment="年度"),
        sa.Column("month", sa.Integer(), nullable=False, comment="月份 1-12"),
        sa.Column("status", sa.String(20), nullable=True, server_default="draft", comment="draft / published / locked"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_site_id"), "schedules", ["site_id"], unique=False)
    op.create_index(op.f("ix_schedules_year_month"), "schedules", ["year", "month"], unique=False)

    op.create_table(
        "schedule_shifts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False, comment="班別日期"),
        sa.Column("shift_code", sa.String(20), nullable=False, comment="日 day / 夜 night / 保留 reserved"),
        sa.Column("start_time", sa.Time(), nullable=True, comment="開始時間"),
        sa.Column("end_time", sa.Time(), nullable=True, comment="結束時間"),
        sa.Column("required_headcount", sa.Integer(), nullable=True, server_default="1", comment="需求人數"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_shifts_schedule_id"), "schedule_shifts", ["schedule_id"], unique=False)
    op.create_index(op.f("ix_schedule_shifts_date"), "schedule_shifts", ["date"], unique=False)

    op.create_table(
        "schedule_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=True, server_default="normal", comment="隊長 leader / 哨點 post / 一般 normal"),
        sa.Column("confirmed", sa.Boolean(), nullable=True, server_default="0", comment="是否確認"),
        sa.Column("notes", sa.String(200), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["schedule_shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_assignments_shift_id"), "schedule_assignments", ["shift_id"], unique=False)
    op.create_index(op.f("ix_schedule_assignments_employee_id"), "schedule_assignments", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_schedule_assignments_employee_id"), table_name="schedule_assignments")
    op.drop_index(op.f("ix_schedule_assignments_shift_id"), table_name="schedule_assignments")
    op.drop_table("schedule_assignments")
    op.drop_index(op.f("ix_schedule_shifts_date"), table_name="schedule_shifts")
    op.drop_index(op.f("ix_schedule_shifts_schedule_id"), table_name="schedule_shifts")
    op.drop_table("schedule_shifts")
    op.drop_index(op.f("ix_schedules_year_month"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_site_id"), table_name="schedules")
    op.drop_table("schedules")
