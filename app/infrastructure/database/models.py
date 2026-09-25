from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""


class WarehouseModel(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_streets: Mapped[int] = mapped_column(Integer, nullable=False)
    total_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    total_levels: Mapped[int] = mapped_column(Integer, nullable=False)
    dock_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dock_y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dock_z: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    slots: Mapped[list["SlotModel"]] = relationship(
        "SlotModel", back_populates="warehouse", cascade="all, delete-orphan"
    )


class SlotModel(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    z: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="FREE", nullable=False)

    warehouse: Mapped["WarehouseModel"] = relationship(
        "WarehouseModel", back_populates="slots"
    )
    coffee_batch: Mapped[Optional["CoffeeBatchModel"]] = relationship(
        "CoffeeBatchModel",
        back_populates="slot",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", "x", "y", "z", name="uq_warehouse_slot_coords"),
        Index("ix_slots_warehouse_coords", "warehouse_id", "x", "y", "z"),
        Index("ix_slots_warehouse_status", "warehouse_id", "status"),
    )


class CoffeeBatchModel(Base):
    __tablename__ = "coffee_batches"

    batch_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    slot_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("slots.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    cooperative_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    coffee_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    harvest_year: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    slot: Mapped[Optional["SlotModel"]] = relationship(
        "SlotModel", back_populates="coffee_batch"
    )


class InventoryMovementModel(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    from_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    from_z: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_z: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )


class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), default="LEGACY_ERP", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
