"""add adaptive learning models (interaction, knowledge_state)

Revision ID: c1d2e3f4a5b6
Revises: 846387a88e28
Create Date: 2026-11-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = '846387a88e28'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'interaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('concept', sa.String(length=120), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interaction_concept'), 'interaction', ['concept'], unique=False)
    op.create_index(op.f('ix_interaction_course_id'), 'interaction', ['course_id'], unique=False)
    op.create_index(op.f('ix_interaction_user_id'), 'interaction', ['user_id'], unique=False)

    op.create_table(
        'knowledge_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('concept', sa.String(length=120), nullable=False),
        sa.Column('mastery', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'concept', name='uq_user_concept')
    )
    op.create_index(op.f('ix_knowledge_state_concept'), 'knowledge_state', ['concept'], unique=False)
    op.create_index(op.f('ix_knowledge_state_user_id'), 'knowledge_state', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_knowledge_state_user_id'), table_name='knowledge_state')
    op.drop_index(op.f('ix_knowledge_state_concept'), table_name='knowledge_state')
    op.drop_table('knowledge_state')
    op.drop_index(op.f('ix_interaction_user_id'), table_name='interaction')
    op.drop_index(op.f('ix_interaction_course_id'), table_name='interaction')
    op.drop_index(op.f('ix_interaction_concept'), table_name='interaction')
    op.drop_table('interaction')
