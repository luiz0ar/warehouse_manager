from datetime import UTC, datetime

import pytest

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse


def test_coffee_bag_creation_valid() -> None:
    bag = CoffeeBag(
        batch_id="BATCH-001",
        cooperative_id="COOP-A",
        coffee_type="ARABICA",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
        weight_kg=60.0,
    )
    assert bag.batch_id == "BATCH-001"
    assert bag.weight_kg == 60.0


def test_coffee_bag_invalid_fields() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="batch_id"):
        CoffeeBag("", "COOP-A", "ARABICA", 2026, now)

    with pytest.raises(ValueError, match="cooperative_id"):
        CoffeeBag("BATCH-001", "  ", "ARABICA", 2026, now)

    with pytest.raises(ValueError, match="coffee_type"):
        CoffeeBag("BATCH-001", "COOP-A", "", 2026, now)

    with pytest.raises(ValueError, match="weight_kg"):
        CoffeeBag("BATCH-001", "COOP-A", "ARABICA", 2026, now, weight_kg=0)


def test_slot_status_invariants() -> None:
    now = datetime.now(UTC)
    coords = Coordinates(1, 2, 0)
    bag = CoffeeBag("BATCH-1", "COOP-1", "ARABICA", 2026, now)

    # Slot FREE with bag -> error
    with pytest.raises(ValueError, match="FREE status cannot have an associated CoffeeBag"):
        Slot(coordinates=coords, status=SlotStatus.FREE, bag=bag)

    # Slot OCCUPIED without bag -> error
    with pytest.raises(ValueError, match="OCCUPIED status must contain a CoffeeBag"):
        Slot(coordinates=coords, status=SlotStatus.OCCUPIED, bag=None)

    # Valid OCCUPIED slot
    occupied_slot = Slot(coordinates=coords, status=SlotStatus.OCCUPIED, bag=bag)
    assert occupied_slot.is_occupied
    assert not occupied_slot.is_available

    # Valid FREE slot
    free_slot = Slot(coordinates=coords, status=SlotStatus.FREE)
    assert free_slot.is_available
    assert not free_slot.is_occupied


def test_warehouse_boundaries_and_dock() -> None:
    wh = Warehouse(
        warehouse_id="WH-1",
        name="Central Warehouse",
        total_streets=5,
        total_columns=10,
        total_levels=3,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    assert wh.is_within_bounds(Coordinates(0, 0, 0))
    assert wh.is_within_bounds(Coordinates(4, 9, 2))
    assert not wh.is_within_bounds(Coordinates(5, 0, 0))
    assert not wh.is_within_bounds(Coordinates(0, 10, 0))
    assert not wh.is_within_bounds(Coordinates(0, 0, 3))


def test_warehouse_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="total_streets"):
        Warehouse("WH-1", "A", total_streets=0, total_columns=10, total_levels=3)

    with pytest.raises(ValueError, match="total_columns"):
        Warehouse("WH-1", "A", total_streets=5, total_columns=0, total_levels=3)

    with pytest.raises(ValueError, match="total_levels"):
        Warehouse("WH-1", "A", total_streets=5, total_columns=10, total_levels=0)

    with pytest.raises(ValueError, match="outside warehouse bounds"):
        Warehouse(
            "WH-1",
            "A",
            total_streets=5,
            total_columns=10,
            total_levels=3,
            dock_coordinates=Coordinates(10, 0, 0),
        )


def test_warehouse_set_get_slot() -> None:
    wh = Warehouse("WH-1", "A", total_streets=3, total_columns=3, total_levels=3)
    coords = Coordinates(1, 1, 1)
    slot = Slot(coordinates=coords, status=SlotStatus.FREE)

    wh.set_slot(slot)
    assert wh.get_slot(coords) == slot
    assert wh.get_slot(Coordinates(0, 0, 0)) is None

    out_of_bounds_slot = Slot(coordinates=Coordinates(5, 5, 5), status=SlotStatus.FREE)
    with pytest.raises(ValueError, match="exceed the configured bounds"):
        wh.set_slot(out_of_bounds_slot)
