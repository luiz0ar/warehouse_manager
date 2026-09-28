import json
from datetime import datetime
from typing import Any

import numpy as np
import redis.asyncio as aioredis

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse


class RedisGridAdapter:
    """Redis adapter for high-performance 3D grid caching and real-time Pub/Sub events."""

    def __init__(self, redis_client: aioredis.Redis[Any]) -> None:
        self.redis = redis_client

    def _meta_key(self, warehouse_id: str) -> str:
        return f"warehouse:{warehouse_id}:meta"

    def _slots_key(self, warehouse_id: str) -> str:
        return f"warehouse:{warehouse_id}:slots"

    def _tensor_key(self, warehouse_id: str) -> str:
        return f"warehouse:{warehouse_id}:tensor"

    async def set_warehouse_grid(self, warehouse: Warehouse) -> None:
        """Serialize and store warehouse metadata, slot details, and NumPy occupation tensor."""
        meta_payload = {
            "warehouse_id": warehouse.warehouse_id,
            "name": warehouse.name,
            "total_streets": warehouse.total_streets,
            "total_columns": warehouse.total_columns,
            "total_levels": warehouse.total_levels,
            "dock_x": warehouse.dock_coordinates.x,
            "dock_y": warehouse.dock_coordinates.y,
            "dock_z": warehouse.dock_coordinates.z,
        }

        shape = (warehouse.total_streets, warehouse.total_columns, warehouse.total_levels)
        occupied_tensor = np.zeros(shape, dtype=np.uint8)
        slots_payload: dict[str, Any] = {}

        for coords, slot in warehouse.slots.items():
            slot_data: dict[str, Any] = {
                "status": slot.status.value,
                "bag": None,
            }
            if slot.status == SlotStatus.OCCUPIED and slot.bag is not None:
                occupied_tensor[coords.x, coords.y, coords.z] = 1
                slot_data["bag"] = {
                    "batch_id": slot.bag.batch_id,
                    "cooperative_id": slot.bag.cooperative_id,
                    "coffee_type": slot.bag.coffee_type,
                    "harvest_year": slot.bag.harvest_year,
                    "entry_date": slot.bag.entry_date.isoformat(),
                    "weight_kg": slot.bag.weight_kg,
                }
            slots_payload[f"{coords.x},{coords.y},{coords.z}"] = slot_data

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(self._meta_key(warehouse.warehouse_id), json.dumps(meta_payload))
            pipe.set(self._slots_key(warehouse.warehouse_id), json.dumps(slots_payload))
            pipe.set(self._tensor_key(warehouse.warehouse_id), occupied_tensor.tobytes())
            await pipe.execute()

    async def get_warehouse_grid(self, warehouse_id: str) -> Warehouse | None:
        """Retrieve and reconstruct the 3D warehouse domain entity from Redis."""
        meta_raw, slots_raw = await self.redis.mget(
            self._meta_key(warehouse_id), self._slots_key(warehouse_id)
        )

        if not meta_raw or not slots_raw:
            return None

        meta = json.loads(meta_raw)
        slots_dict = json.loads(slots_raw)

        warehouse = Warehouse(
            warehouse_id=meta["warehouse_id"],
            name=meta["name"],
            total_streets=meta["total_streets"],
            total_columns=meta["total_columns"],
            total_levels=meta["total_levels"],
            dock_coordinates=Coordinates(x=meta["dock_x"], y=meta["dock_y"], z=meta["dock_z"]),
        )

        for coord_str, slot_data in slots_dict.items():
            x_str, y_str, z_str = coord_str.split(",")
            coords = Coordinates(x=int(x_str), y=int(y_str), z=int(z_str))

            bag = None
            if slot_data.get("bag"):
                b = slot_data["bag"]
                bag = CoffeeBag(
                    batch_id=b["batch_id"],
                    cooperative_id=b["cooperative_id"],
                    coffee_type=b["coffee_type"],
                    harvest_year=b["harvest_year"],
                    entry_date=datetime.fromisoformat(b["entry_date"]),
                    weight_kg=b["weight_kg"],
                )

            slot = Slot(
                coordinates=coords,
                status=SlotStatus(slot_data["status"]),
                bag=bag,
            )
            warehouse.set_slot(slot)

        return warehouse

    async def get_occupied_tensor(self, warehouse_id: str) -> np.ndarray | None:
        """Extract the raw boolean NumPy 3D tensor directly from Redis for zero-copy operations."""
        meta_raw, tensor_bytes = await self.redis.mget(
            self._meta_key(warehouse_id), self._tensor_key(warehouse_id)
        )

        if not meta_raw or not isinstance(tensor_bytes, (bytes, bytearray, memoryview)):
            return None

        meta = json.loads(meta_raw)
        shape = (meta["total_streets"], meta["total_columns"], meta["total_levels"])
        return np.frombuffer(tensor_bytes, dtype=np.uint8).reshape(shape).astype(bool)

    async def publish_event(self, channel: str, message: dict[str, Any]) -> None:
        """Publish a real-time event via Redis Pub/Sub."""
        await self.redis.publish(channel, json.dumps(message))

    async def invalidate_warehouse_grid(self, warehouse_id: str) -> None:
        """Evict all cached grid keys for a warehouse."""
        await self.redis.delete(
            self._meta_key(warehouse_id),
            self._slots_key(warehouse_id),
            self._tensor_key(warehouse_id),
        )
