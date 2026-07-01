"""user signup anti-abuse signals (ip, fingerprint, flagged)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-01 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('signup_ip', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('signup_fp', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('flagged', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('flag_reason', sa.String(length=60), nullable=True))
    op.create_index(op.f('ix_users_signup_fp'), 'users', ['signup_fp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_signup_fp'), table_name='users')
    op.drop_column('users', 'flag_reason')
    op.drop_column('users', 'flagged')
    op.drop_column('users', 'signup_fp')
    op.drop_column('users', 'signup_ip')
