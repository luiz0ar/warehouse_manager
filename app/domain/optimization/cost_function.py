from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CostParameters:
    """Calibration weights for the linear cost function Z = (alpha * D) + (beta * R).

    alpha: Weight assigned to physical distance traveled from dock to batch.
    beta: Weight assigned to rehandling (removal of obstructing vertical bags).
          Typically beta >> alpha, because operating forklifts vertically to
          remove obstacles consumes significantly more time and energy.
    """

    alpha: float = 1.0
    beta: float = 10.0

    def __post_init__(self) -> None:
        if self.alpha < 0.0:
            raise ValueError(f"Parameter alpha must be non-negative. Received: {self.alpha}")
        if self.beta < 0.0:
            raise ValueError(f"Parameter beta must be non-negative. Received: {self.beta}")


class CostFunction:
    """Evaluator for the Operations Research linear cost function for Picking."""

    def __init__(self, parameters: CostParameters | None = None) -> None:
        self.parameters = parameters or CostParameters()

    def calculate(self, distance: float, blocking_bags: int) -> float:
        """Calculate scalar cost Z = (alpha * D) + (beta * R)."""
        if distance < 0.0:
            raise ValueError("Distance D cannot be negative.")
        if blocking_bags < 0:
            raise ValueError("Blocking bags count R cannot be negative.")

        return float(
            (self.parameters.alpha * distance)
            + (self.parameters.beta * float(blocking_bags))
        )

    def calculate_vectorized(
        self, distances: np.ndarray, blocking_bags: np.ndarray
    ) -> np.ndarray:
        """Calculate vectorized cost Z for multidimensional NumPy arrays."""
        if distances.shape != blocking_bags.shape:
            raise ValueError(
                f"Array shapes must match: {distances.shape} != {blocking_bags.shape}"
            )
        return (self.parameters.alpha * distances) + (self.parameters.beta * blocking_bags)
