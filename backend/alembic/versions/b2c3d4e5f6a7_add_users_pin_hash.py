"""Add users.pin_hash for front-line staff kiosk PIN login

Revision ID: b2c3d4e5f6a7
Revises: a9f0c1d2e3b4
Create Date: 2026-08-11 07:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a9f0c1d2e3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pin_hash", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pin_hash")
