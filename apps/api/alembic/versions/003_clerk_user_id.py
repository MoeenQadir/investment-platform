"""clerk user id

Revision ID: 003_clerk_user_id
Revises: 002_edgar
Create Date: 2026-05-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003_clerk_user_id'
down_revision = '002_edgar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('clerk_user_id', sa.String(), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        'ix_users_clerk_user_id',
        'users',
        ['clerk_user_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_users_clerk_user_id', table_name='users')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'clerk_user_id')
