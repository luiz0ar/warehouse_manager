from dataclasses import FrozenInstanceError

import pytest

from app.domain.models.coordinates import Coordinates


def test_coordinates_valid_initialization() -> None:
    coords = Coordinates(x=2, y=5, z=1)
    assert coords.x == 2
    assert coords.y == 5
    assert coords.z == 1


def test_coordinates_negative_values_raise_error() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Coordinates(x=-1, y=0, z=0)

    with pytest.raises(ValueError, match="non-negative"):
        Coordinates(x=0, y=-2, z=0)

    with pytest.raises(ValueError, match="non-negative"):
        Coordinates(x=0, y=0, z=-3)


def test_coordinates_immutability() -> None:
    coords = Coordinates(x=1, y=1, z=1)
    with pytest.raises(FrozenInstanceError):
        coords.x = 2  # type: ignore[misc]


def test_coordinates_manhattan_distance() -> None:
    c1 = Coordinates(0, 0, 0)
    c2 = Coordinates(3, 4, 2)
    assert c1.manhattan_distance_to(c2) == 9.0

    c3 = Coordinates(5, 5, 3)
    c4 = Coordinates(2, 1, 0)
    # |5-2| + |5-1| + |3-0| = 3 + 4 + 3 = 10
    assert c3.manhattan_distance_to(c4) == 10.0


def test_coordinates_euclidean_distance() -> None:
    c1 = Coordinates(0, 0, 0)
    c2 = Coordinates(3, 4, 0)
    assert c1.euclidean_distance_to(c2) == 5.0

    c3 = Coordinates(1, 2, 2)
    c4 = Coordinates(1, 2, 2)
    assert c3.euclidean_distance_to(c4) == 0.0
