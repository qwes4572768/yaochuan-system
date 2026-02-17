"""initial schema - employees, dependents, documents, insurance_config

Revision ID: 001
Revises:
Create Date: 2025-01-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_no", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("id_number", sa.String(500), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("position", sa.String(50), nullable=True),
        sa.Column("department", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("bank_account", sa.String(500), nullable=True),
        sa.Column("insured_salary", sa.Numeric(12, 2), nullable=True),
        sa.Column("group_insurance_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_employee_no"), "employees", ["employee_no"], unique=True)

    op.create_table(
        "dependents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("relation", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("id_number", sa.String(500), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("is_insured", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dependents_employee_id"), "dependents", ["employee_id"], unique=False)

    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employee_documents_employee_id"), "employee_documents", ["employee_id"], unique=False)

    op.create_table(
        "insurance_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_key", sa.String(50), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_insurance_config_config_key"), "insurance_config", ["config_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_insurance_config_config_key"), table_name="insurance_config")
    op.drop_table("insurance_config")
    op.drop_index(op.f("ix_employee_documents_employee_id"), table_name="employee_documents")
    op.drop_table("employee_documents")
    op.drop_index(op.f("ix_dependents_employee_id"), table_name="dependents")
    op.drop_table("dependents")
    op.drop_index(op.f("ix_employees_employee_no"), table_name="employees")
    op.drop_table("employees")
