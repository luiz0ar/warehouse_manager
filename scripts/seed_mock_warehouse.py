import asyncio
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import setup_logging
from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory


async def seed_warehouse(
    warehouse_id: str = "WH-MINASUL-01",
    name: str = "Armazém Regional Sul de Minas - Minasul",
    total_streets: int = 4,
    total_columns: int = 10,
    total_levels: int = 4,
) -> None:
    """Populate database and Redis grid with a realistic mock coffee warehouse."""
    setup_logging()
    print("=" * 70)
    print(f"[*] Initializing mock warehouse: {warehouse_id} ('{name}')")
    print(
        f"[*] Topology: {total_streets} Streets x {total_columns} Columns x {total_levels} Levels"
    )
    print(f"[*] Total Positions: {total_streets * total_columns * total_levels} slots")
    print("=" * 70)

    random.seed(42)

    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        name=name,
        total_streets=total_streets,
        total_columns=total_columns,
        total_levels=total_levels,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    coffee_types = [
        "BOURBON_AMARELO",
        "CATUAI_VERMELHO",
        "ARABICA_SPECIAL",
        "MUNDO_NOVO",
    ]

    cooperatives = [
        "COOP-MINASUL",
        "COOP-VARGINHA",
        "COOP-ALFENAS",
        "COOP-POCOS",
    ]

    occupied_count = 0
    free_count = 0
    batch_counter = 1000

    for x in range(total_streets):
        for y in range(total_columns):
            if x == 0 and y == 0:
                for z in range(total_levels):
                    warehouse.set_slot(
                        Slot(coordinates=Coordinates(x, y, z), status=SlotStatus.FREE)
                    )
                    free_count += 1
                continue

            stack_height = random.choices([0, 1, 2, 3, 4], weights=[0.1, 0.2, 0.3, 0.25, 0.15])[0]

            for z in range(total_levels):
                coords = Coordinates(x, y, z)
                if z < stack_height:
                    batch_counter += 1
                    batch_id = f"LOT-{batch_counter}"
                    c_type = random.choice(coffee_types)
                    coop = random.choice(cooperatives)
                    harvest = random.choice([2024, 2025, 2026])

                    bag = CoffeeBag(
                        batch_id=batch_id,
                        cooperative_id=coop,
                        coffee_type=c_type,
                        harvest_year=harvest,
                        entry_date=datetime.now(UTC),
                        weight_kg=60.0,
                    )
                    slot = Slot(coordinates=coords, status=SlotStatus.OCCUPIED, bag=bag)
                    warehouse.set_slot(slot)
                    occupied_count += 1
                else:
                    slot = Slot(coordinates=coords, status=SlotStatus.FREE)
                    warehouse.set_slot(slot)
                    free_count += 1

    print("\n[+] Persisting warehouse ground truth to PostgreSQL...")
    async with async_session_factory() as session:
        repository = SqlAlchemyWarehouseRepository(session)
        await repository.save_warehouse(warehouse)
        for slot in warehouse.slots.values():
            await repository.update_slot(warehouse.warehouse_id, slot)
    print("[OK] PostgreSQL persistence complete.")

    print("[+] Synchronizing 3D tensor and slots to Redis cache...")
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    try:
        grid_cache = RedisGridAdapter(redis_client)
        await grid_cache.set_warehouse_grid(warehouse)
    finally:
        await redis_client.aclose()
    print("[OK] Redis cache synchronized.")

    print("\n" + "=" * 70)
    print("[DONE] Mock Warehouse Seeding Finished Successfully!")
    print(f"  * Warehouse ID: {warehouse_id}")
    print(f"  * Occupied Slots: {occupied_count} bags")
    print(f"  * Available Free Slots: {free_count}")
    print("=" * 70)
    print("\n[INFO] Ready for testing:")
    print("  1. View full 3D grid layout:")
    print(f"     curl -X GET http://localhost:8000/api/v1/warehouses/{warehouse_id}/grid")
    print("\n  2. Test Picking Optimization:")
    print("     curl -X POST http://localhost:8000/api/v1/picking/recommend \\")
    print('          -H "Content-Type: application/json" \\')
    print(
        f'          -d \'{{"warehouse_id": "{warehouse_id}", "coffee_type": "BOURBON_AMARELO", "max_recommendations": 3}}\''
    )
    print("\n  3. Interactive Swagger UI:")
    print("     http://localhost:8000/docs")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(seed_warehouse())
