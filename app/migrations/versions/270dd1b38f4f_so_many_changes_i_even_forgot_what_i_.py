"""so many changes i even forgot what i changed

Revision ID: 270dd1b38f4f
Revises: 6966cd64352c
Create Date: 2024-10-18 17:02:47.917129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '270dd1b38f4f'
down_revision = '6966cd64352c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_constraint('fk_invoices_customer_id_customers', type_='foreignkey')
        batch_op.drop_column('customer_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_id', sa.INTEGER(), nullable=False))
        batch_op.create_foreign_key('fk_invoices_customer_id_customers', 'customers', ['customer_id'], ['id'])

    # ### end Alembic commands ###