"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Portfolios
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_id'), 'portfolios', ['id'], unique=False)

    # Holdings
    op.create_table(
        'holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('ticker_symbol', sa.String(), nullable=False),
        sa.Column('marketplace', sa.String(), nullable=False),
        sa.Column('exchange', sa.String(), nullable=False),
        sa.Column('provider_symbol', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('buy_date', sa.Date(), nullable=False),
        sa.Column('buy_price', sa.Float(), nullable=False),
        sa.Column('broker', sa.String(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_holdings_id'), 'holdings', ['id'], unique=False)
    op.create_index(op.f('ix_holdings_provider_symbol'), 'holdings', ['provider_symbol'], unique=False)

    # Research Runs
    op.create_table(
        'research_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=True),
        sa.Column('run_type', sa.Enum('RESEARCH', 'EXPLAIN', name='runtype'), nullable=False),
        sa.Column('trigger_type', sa.Enum('PRICE_MOVE', 'FILING_EVENT', 'SCHEDULED', name='triggertype'), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED', name='runstatus'), nullable=False),
        sa.Column('params_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('holdings_snapshot_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metrics_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('report_md', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Run Sources
    op.create_table(
        'run_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_sources_id'), 'run_sources', ['id'], unique=False)

    # Canonical Sectors
    op.create_table(
        'canonical_sectors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_name')
    )

    # Sector Aliases
    op.create_table(
        'sector_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('alias', sa.String(), nullable=False),
        sa.Column('canonical_sector_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['canonical_sector_id'], ['canonical_sectors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Sector ETF Proxies
    op.create_table(
        'sector_etf_proxies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(), nullable=False),
        sa.Column('canonical_sector_id', sa.Integer(), nullable=False),
        sa.Column('etf_symbol', sa.String(), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['canonical_sector_id'], ['canonical_sectors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sector_etf_proxies')
    op.drop_table('sector_aliases')
    op.drop_table('canonical_sectors')
    op.drop_table('run_sources')
    op.drop_table('research_runs')
    op.drop_table('holdings')
    op.drop_table('portfolios')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS runstatus')
    op.execute('DROP TYPE IF EXISTS triggertype')
    op.execute('DROP TYPE IF EXISTS runtype')

