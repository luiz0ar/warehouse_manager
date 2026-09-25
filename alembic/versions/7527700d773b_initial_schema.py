"""initial_schema

Revision ID: 7527700d773b
Revises:
Create Date: 2026-09-25 15:57:44.906782

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '7527700d773b'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('idempotency_keys',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('warehouses',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('total_streets', sa.Integer(), nullable=False),
    sa.Column('total_columns', sa.Integer(), nullable=False),
    sa.Column('total_levels', sa.Integer(), nullable=False),
    sa.Column('dock_x', sa.Integer(), nullable=False),
    sa.Column('dock_y', sa.Integer(), nullable=False),
    sa.Column('dock_z', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('inventory_movements',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('warehouse_id', sa.String(length=50), nullable=False),
    sa.Column('batch_id', sa.String(length=50), nullable=False),
    sa.Column('movement_type', sa.String(length=30), nullable=False),
    sa.Column('from_x', sa.Integer(), nullable=True),
    sa.Column('from_y', sa.Integer(), nullable=True),
    sa.Column('from_z', sa.Integer(), nullable=True),
    sa.Column('to_x', sa.Integer(), nullable=True),
    sa.Column('to_y', sa.Integer(), nullable=True),
    sa.Column('to_z', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_movements_batch_id'), 'inventory_movements', ['batch_id'], unique=False)
    op.create_index(op.f('ix_inventory_movements_timestamp'), 'inventory_movements', ['timestamp'], unique=False)
    op.create_table('slots',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('warehouse_id', sa.String(length=50), nullable=False),
    sa.Column('x', sa.Integer(), nullable=False),
    sa.Column('y', sa.Integer(), nullable=False),
    sa.Column('z', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('warehouse_id', 'x', 'y', 'z', name='uq_warehouse_slot_coords')
    )
    op.create_index('ix_slots_warehouse_coords', 'slots', ['warehouse_id', 'x', 'y', 'z'], unique=False)
    op.create_index('ix_slots_warehouse_status', 'slots', ['warehouse_id', 'status'], unique=False)
    op.create_table('coffee_batches',
    sa.Column('batch_id', sa.String(length=50), nullable=False),
    sa.Column('slot_id', sa.Integer(), nullable=True),
    sa.Column('cooperative_id', sa.String(length=50), nullable=False),
    sa.Column('coffee_type', sa.String(length=50), nullable=False),
    sa.Column('harvest_year', sa.Integer(), nullable=False),
    sa.Column('entry_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['slot_id'], ['slots.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('batch_id'),
    sa.UniqueConstraint('slot_id')
    )
    op.create_index(op.f('ix_coffee_batches_coffee_type'), 'coffee_batches', ['coffee_type'], unique=False)
    op.create_index(op.f('ix_coffee_batches_cooperative_id'), 'coffee_batches', ['cooperative_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_coffee_batches_cooperative_id'), table_name='coffee_batches')
    op.drop_index(op.f('ix_coffee_batches_coffee_type'), table_name='coffee_batches')
    op.drop_table('coffee_batches')
    op.drop_index('ix_slots_warehouse_status', table_name='slots')
    op.drop_index('ix_slots_warehouse_coords', table_name='slots')
    op.drop_table('slots')
    op.drop_index(op.f('ix_inventory_movements_timestamp'), table_name='inventory_movements')
    op.drop_index(op.f('ix_inventory_movements_batch_id'), table_name='inventory_movements')
    op.drop_table('inventory_movements')
    op.drop_table('warehouses')
    op.drop_table('idempotency_keys')