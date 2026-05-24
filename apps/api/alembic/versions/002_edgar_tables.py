"""edgar tables

Revision ID: 002_edgar
Revises: 001_initial
Create Date: 2026-05-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '002_edgar'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sec_companies',
        sa.Column('cik', sa.String(length=10), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('cik'),
    )
    op.create_index(op.f('ix_sec_companies_ticker'), 'sec_companies', ['ticker'], unique=False)

    op.create_table(
        'sec_filings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cik', sa.String(length=10), nullable=False),
        sa.Column('accession_no', sa.String(), nullable=False),
        sa.Column('form_type', sa.String(), nullable=False),
        sa.Column('filed_at', sa.DateTime(), nullable=False),
        sa.Column('period_of_report', sa.Date(), nullable=True),
        sa.Column('primary_doc_url', sa.String(), nullable=True),
        sa.Column('filing_index_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cik'], ['sec_companies.cik']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('accession_no', name='uq_sec_filings_accession_no'),
    )
    op.create_index(op.f('ix_sec_filings_id'), 'sec_filings', ['id'], unique=False)
    op.create_index(op.f('ix_sec_filings_cik'), 'sec_filings', ['cik'], unique=False)
    op.create_index(op.f('ix_sec_filings_accession_no'), 'sec_filings', ['accession_no'], unique=True)
    op.create_index(op.f('ix_sec_filings_form_type'), 'sec_filings', ['form_type'], unique=False)
    op.create_index(op.f('ix_sec_filings_filed_at'), 'sec_filings', ['filed_at'], unique=False)

    op.create_table(
        'sec_form4_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.Column('cik', sa.String(length=10), nullable=False),
        sa.Column('issuer_cik', sa.String(length=10), nullable=True),
        sa.Column('issuer_ticker', sa.String(), nullable=True),
        sa.Column('insider_name', sa.String(), nullable=False),
        sa.Column('insider_cik', sa.String(length=10), nullable=True),
        sa.Column('relationship_type', sa.String(), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('transaction_code', sa.String(length=2), nullable=True),
        sa.Column('security_title', sa.String(), nullable=True),
        sa.Column('shares', sa.Float(), nullable=True),
        sa.Column('price_per_share', sa.Float(), nullable=True),
        sa.Column('acquired_disposed_code', sa.String(length=1), nullable=True),
        sa.Column('shares_owned_following', sa.Float(), nullable=True),
        sa.Column('is_derivative', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['sec_filings.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sec_form4_transactions_id'), 'sec_form4_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_sec_form4_transactions_filing_id'), 'sec_form4_transactions', ['filing_id'], unique=False)
    op.create_index(op.f('ix_sec_form4_transactions_cik'), 'sec_form4_transactions', ['cik'], unique=False)
    op.create_index(op.f('ix_sec_form4_transactions_issuer_cik'), 'sec_form4_transactions', ['issuer_cik'], unique=False)
    op.create_index(op.f('ix_sec_form4_transactions_issuer_ticker'), 'sec_form4_transactions', ['issuer_ticker'], unique=False)
    op.create_index(op.f('ix_sec_form4_transactions_transaction_date'), 'sec_form4_transactions', ['transaction_date'], unique=False)


def downgrade() -> None:
    op.drop_table('sec_form4_transactions')
    op.drop_table('sec_filings')
    op.drop_table('sec_companies')
