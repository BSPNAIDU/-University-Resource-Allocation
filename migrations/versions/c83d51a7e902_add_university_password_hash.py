"""Add university password hash

Revision ID: c83d51a7e902
Revises: b72c91d4e605
"""
from alembic import op
import sqlalchemy as sa

revision = "c83d51a7e902"
down_revision = "b72c91d4e605"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "universities",
        sa.Column("password_hash", sa.String(length=255), nullable=True)
    )


def downgrade():
    op.drop_column("universities", "password_hash")
