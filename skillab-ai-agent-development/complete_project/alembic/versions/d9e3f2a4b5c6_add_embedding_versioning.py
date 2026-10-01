"""add embedding versioning

Revision ID: d9e3f2a4b5c6
Revises: c8f2a1b3d4e5
Create Date: 2026-07-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e3f2a4b5c6'
down_revision: Union[str, None] = 'c8f2a1b3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to document_chunks
    op.add_column(
        'document_chunks',
        sa.Column('content_hash', sa.String(32), nullable=True)
    )
    op.add_column(
        'document_chunks',
        sa.Column('embedding_model', sa.String(100), nullable=True)
    )
    op.add_column(
        'document_chunks',
        sa.Column('embedding_version', sa.String(20), nullable=True)
    )
    # Create index on content_hash for deduplication
    op.create_index(
        'ix_document_chunks_content_hash',
        'document_chunks',
        ['content_hash'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_document_chunks_content_hash', table_name='document_chunks')
    op.drop_column('document_chunks', 'embedding_version')
    op.drop_column('document_chunks', 'embedding_model')
    op.drop_column('document_chunks', 'content_hash')
