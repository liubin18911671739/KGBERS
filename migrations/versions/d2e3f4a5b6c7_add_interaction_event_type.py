"""add interaction event_type for completion semantics

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-11-16 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'interaction',
        sa.Column(
            'event_type',
            sa.String(length=16),
            server_default='answer',
            nullable=False,
        ),
    )
    op.create_index(
        op.f('ix_interaction_event_type'),
        'interaction',
        ['event_type'],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f('ix_interaction_event_type'), table_name='interaction'
    )
    op.drop_column('interaction', 'event_type')
