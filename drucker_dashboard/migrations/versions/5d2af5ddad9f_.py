"""empty message

Revision ID: 5d2af5ddad9f
Revises:
Create Date: 2018-08-27 02:56:57.095690

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5d2af5ddad9f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('service_name', table_name='model_assignments')
    op.drop_table('model_assignments')
    op.create_unique_constraint(None, 'kubernetes', ['dns_name'])
    op.drop_index('service_name', table_name='services')
    op.create_unique_constraint(None, 'services', ['service_name'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'services', type_='unique')
    op.create_index('service_name', 'services', ['service_name', 'service_level'], unique=True)
    op.drop_constraint(None, 'kubernetes', type_='unique')
    op.create_table('model_assignments',
    sa.Column('service_name', mysql.VARCHAR(length=512), nullable=False),
    sa.Column('model_path', mysql.VARCHAR(length=512), nullable=False),
    sa.Column('first_boot', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('service_name'),
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('service_name', 'model_assignments', ['service_name'], unique=True)
    # ### end Alembic commands ###