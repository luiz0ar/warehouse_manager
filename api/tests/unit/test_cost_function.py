import numpy as np
import pytest

from app.domain.optimization.cost_function import CostFunction, CostParameters


def test_cost_function_default_parameters() -> None:
    cf = CostFunction()
    # Z = (1.0 * 10) + (10.0 * 2) = 10 + 20 = 30.0
    cost = cf.calculate(distance=10.0, blocking_bags=2)
    assert cost == 30.0


def test_cost_function_custom_parameters() -> None:
    params = CostParameters(alpha=0.5, beta=20.0)
    cf = CostFunction(params)
    # Z = (0.5 * 10) + (20.0 * 1) = 5 + 20 = 25.0
    cost = cf.calculate(distance=10.0, blocking_bags=1)
    assert cost == 25.0


def test_cost_function_invalid_inputs() -> None:
    cf = CostFunction()
    with pytest.raises(ValueError, match="Distance"):
        cf.calculate(distance=-1.0, blocking_bags=0)

    with pytest.raises(ValueError, match="Blocking bags"):
        cf.calculate(distance=5.0, blocking_bags=-1)

    with pytest.raises(ValueError, match="alpha"):
        CostParameters(alpha=-1.0)

    with pytest.raises(ValueError, match="beta"):
        CostParameters(beta=-5.0)


def test_cost_function_vectorized() -> None:
    cf = CostFunction(CostParameters(alpha=1.0, beta=10.0))
    distances = np.array([5.0, 10.0, 15.0])
    blocking = np.array([0, 1, 2])

    expected = np.array([5.0, 20.0, 35.0])
    result = cf.calculate_vectorized(distances, blocking)
    np.testing.assert_allclose(result, expected)


def test_cost_function_vectorized_shape_mismatch() -> None:
    cf = CostFunction()
    distances = np.array([5.0, 10.0])
    blocking = np.array([0, 1, 2])
    with pytest.raises(ValueError, match="shapes must match"):
        cf.calculate_vectorized(distances, blocking)
