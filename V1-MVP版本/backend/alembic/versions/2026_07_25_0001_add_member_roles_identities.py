"""add member roles and identities

Revision ID: 2026_07_25_0001
Revises:
Create Date: 2026-07-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_25_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column("roles", sa.JSON(), nullable=True),
    )
    op.add_column(
        "members",
        sa.Column("identities", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("members", "identities")
    op.drop_column("members", "roles")
