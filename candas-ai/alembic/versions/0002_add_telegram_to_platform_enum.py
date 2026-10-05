"""add telegram to platform enum

Revision ID: 0002_telegram_platform
Revises: 0001_initial
Create Date: 2026-06-11
"""

from alembic import op

revision = '0002_telegram_platform'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'telegram'")


def downgrade():
    # PostgreSQL enum value removal is intentionally not automated here.
    pass
