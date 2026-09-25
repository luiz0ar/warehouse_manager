class DomainError(Exception):
    """Base domain exception."""

class WarehouseNotFoundError(DomainError):
    """Raised when a warehouse is not found in database or cache."""

    def __init__(self, warehouse_id: str) -> None:
        super().__init__(f"Warehouse '{warehouse_id}' was not found.")
        self.warehouse_id = warehouse_id


class EntityConflictError(DomainError):
    """Raised on unique constraint or duplicate entity conflict."""