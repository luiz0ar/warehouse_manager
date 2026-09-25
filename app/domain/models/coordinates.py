import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinates:
    """Three-dimensional physical coordinates in the warehouse [X, Y, Z].

    X: Street / Operational aisle
    Y: Stack / Column depth
    Z: Vertical stacking level
    """

    x: int
    y: int
    z: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.z < 0:
            raise ValueError(
                f"Coordinates must be non-negative integers: x={self.x}, y={self.y}, z={self.z}"
            )

    def manhattan_distance_to(self, other: "Coordinates") -> float:
        """Calculate 3D Manhattan distance (|dx| + |dy| + |dz|)."""
        return float(abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z))

    def euclidean_distance_to(self, other: "Coordinates") -> float:
        """Calculate 3D Euclidean distance."""
        return float(
            math.sqrt(
                (self.x - other.x) ** 2
                + (self.y - other.y) ** 2
                + (self.z - other.z) ** 2
            )
        )
