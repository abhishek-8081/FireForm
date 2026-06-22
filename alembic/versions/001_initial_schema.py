"""Initial schema — Template and FormSubmission tables.

Revision ID: 001
Revises:
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "template",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString, nullable=False),
        sa.Column("fields", sa.JSON, nullable=False),
        sa.Column("pdf_path", sqlmodel.sql.sqltypes.AutoString, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "formsubmission",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("template.id"), nullable=False),
        sa.Column("input_text", sqlmodel.sql.sqltypes.AutoString, nullable=False),
        sa.Column("output_pdf_path", sqlmodel.sql.sqltypes.AutoString, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("formsubmission")
    op.drop_table("template")
