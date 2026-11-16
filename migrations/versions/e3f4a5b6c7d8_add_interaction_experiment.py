"""add experiment dimension to interaction

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-16 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'interaction',
        sa.Column(
            'experiment',
            sa.String(length=64),
            server_default='recommendation',
            nullable=False,
        ),
    )
    op.add_column(
        'interaction',
        sa.Column('variant', sa.String(length=32), nullable=True),
    )
    op.create_index(
        op.f('ix_interaction_experiment'),
        'interaction',
        ['experiment'],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f('ix_interaction_experiment'), table_name='interaction'
    )
    op.drop_column('interaction', 'variant')
    op.drop_column('interaction', 'experiment')
