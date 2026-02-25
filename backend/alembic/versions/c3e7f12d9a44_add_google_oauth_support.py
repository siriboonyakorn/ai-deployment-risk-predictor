"""add google oauth support

Revision ID: c3e7f12d9a44
Revises: b092ad8a8c01
Create Date: 2026-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e7f12d9a44'
down_revision: Union[str, None] = 'b092ad8a8c01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add google_id column to users
    op.add_column('users', sa.Column('google_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)

    # Make github_id nullable so Google-only users can be stored.
    # SQLite does not support ALTER COLUMN directly, so we use batch mode.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'github_id',
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'github_id',
            existing_type=sa.Integer(),
            nullable=False,
        )

    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'google_id')
