"""pickle

Revision ID: 59b8a4df4537
Revises: 5302c307d7eb
Create Date: 2025-04-27 12:03:03.329138

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '59b8a4df4537'
down_revision = '5302c307d7eb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('workflow_temp_vars', schema=None) as batch_op:
        batch_op.alter_column('value',
               existing_type=sqlite.JSON(),
               type_=sa.PickleType(),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('workflow_temp_vars', schema=None) as batch_op:
        batch_op.alter_column('value',
               existing_type=sa.PickleType(),
               type_=sqlite.JSON(),
               existing_nullable=True)

    # ### end Alembic commands ###
