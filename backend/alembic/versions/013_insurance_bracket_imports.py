"""insurance_bracket_imports + insurance_brackets：勞健保級距表匯入（權威資料）

Revision ID: 013
Revises: 012
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insurance_bracket_imports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False, comment="原始檔名"),
        sa.Column("file_path", sa.String(500), nullable=True, comment="原檔儲存路徑，供下載備查"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0", comment="匯入筆數（級距列數）"),
        sa.Column("version", sa.String(60), nullable=True, comment="版本或備註"),
        sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "insurance_brackets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("insured_salary_level", sa.Integer(), nullable=False, comment="投保薪資級距（整數）"),
        sa.Column("labor_employer", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("labor_employee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("health_employer", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("health_employee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("occupational_accident", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("labor_pension", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("group_insurance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["import_id"], ["insurance_bracket_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_insurance_brackets_import_id"), "insurance_brackets", ["import_id"], unique=False)
    op.create_index(
        "ix_ins_brk_import_level",
        "insurance_brackets",
        ["import_id", "insured_salary_level"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_ins_brk_import_level", table_name="insurance_brackets")
    op.drop_index(op.f("ix_insurance_brackets_import_id"), table_name="insurance_brackets")
    op.drop_table("insurance_brackets")
    op.drop_table("insurance_bracket_imports")
