"""add clerk_user_id to users

Revision ID: d5a2e89f3b71
Revises: c3e7f12d9a44
Create Date: 2026-02-25 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a2e89f3b71'
down_revision: Union[str, None] = 'c3e7f12d9a44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add clerk_user_id column (primary auth identifier going forward)
    op.add_column(
        'users',
        sa.Column('clerk_user_id', sa.String(length=128), nullable=True),
    )
    op.create_index(
        op.f('ix_users_clerk_user_id'),
        'users',
        ['clerk_user_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_users_clerk_user_id'), table_name='users')
    op.drop_column('users', 'clerk_user_id')
