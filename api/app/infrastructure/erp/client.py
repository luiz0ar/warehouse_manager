from datetime import datetime
from typing import Protocol

import structlog

from app.infrastructure.erp.models import ERPMovementRecord

logger = structlog.get_logger()


class LegacyERPClientPort(Protocol):
    """Port for querying the external legacy ERP system (SELECT-only)."""

    async def fetch_pending_movements(
        self, since: datetime | None = None, limit: int = 100
    ) -> list[ERPMovementRecord]:
        """Fetch uncommitted or recent inventory movements from ERP."""
        ...


class SimulatedLegacyERPClient:
    """In-memory simulated legacy ERP client for testing and local shadow state synchronization.

    Conforms to the SELECT-only principle: never performs writes to ERP tables.
    """

    def __init__(self) -> None:
        self._records: list[ERPMovementRecord] = []

    def feed_movement(self, record: ERPMovementRecord) -> None:
        """Inject a movement record into the simulated ERP queue for testing."""
        self._records.append(record)
        logger.debug(
            "simulated_erp_movement_enqueued",
            event_id=record.event_id,
            batch_id=record.batch_id,
            movement_type=record.movement_type.value,
        )

    def clear(self) -> None:
        """Clear all stored records (useful for test teardown)."""
        self._records.clear()

    async def fetch_pending_movements(
        self, since: datetime | None = None, limit: int = 100
    ) -> list[ERPMovementRecord]:
        """Query recent movements matching criteria (SELECT-only)."""
        filtered = self._records
        if since is not None:
            filtered = [r for r in filtered if r.timestamp >= since]

        # Return up to limit
        return filtered[:limit]


# Module singleton instance for shared simulated polling
simulated_erp_client = SimulatedLegacyERPClient()
