"""add extraction tables

Revision ID: c8f2a1b3d4e5
Revises: b71305bc755a
Create Date: 2026-07-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f2a1b3d4e5'
down_revision: Union[str, None] = 'b71305bc755a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extracted_invoices table
    op.create_table(
        'extracted_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('numar', sa.String(length=100), nullable=True),
        sa.Column('data', sa.String(length=50), nullable=True),
        sa.Column('furnizor', sa.String(length=500), nullable=True),
        sa.Column('client', sa.String(length=500), nullable=True),
        sa.Column('produse_json', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('tva', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_extracted_invoices_file_name'),
        'extracted_invoices',
        ['file_name'],
        unique=False
    )

    # Create extracted_contracts table
    op.create_table(
        'extracted_contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('numar', sa.String(length=100), nullable=True),
        sa.Column('data_incheiere', sa.String(length=50), nullable=True),
        sa.Column('prestator', sa.String(length=500), nullable=True),
        sa.Column('beneficiar', sa.String(length=500), nullable=True),
        sa.Column('valoare', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('durata_luni', sa.Integer(), nullable=True),
        sa.Column('obligatii_json', sa.Text(), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_extracted_contracts_file_name'),
        'extracted_contracts',
        ['file_name'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_extracted_contracts_file_name'), table_name='extracted_contracts')
    op.drop_table('extracted_contracts')
    op.drop_index(op.f('ix_extracted_invoices_file_name'), table_name='extracted_invoices')
    op.drop_table('extracted_invoices')
