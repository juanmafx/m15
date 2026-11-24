from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import sqrt
from operator import ge, le


@dataclass(frozen=True, slots=True)
class WindowMoments:
    mean: float
    std: float


def _require_window(window: int) -> None:
    if window <= 0:
        raise ValueError("window must be positive")


def rolling_moments(values: Sequence[float], window: int) -> list[WindowMoments]:
    _require_window(window)
    if window == 1:
        return [WindowMoments(value, 0.0) for value in values]
    results: list[WindowMoments] = []
    mean = 0.0
    scatter = 0.0
    for index, value in enumerate(values):
        if index < window:
            delta = value - mean
            mean += delta / (index + 1)
            scatter += delta * (value - mean)
        else:
            leaving = values[index - window]
            previous_mean = mean
            mean += (value - leaving) / window
            scatter += (value - leaving) * (value - mean + leaving - previous_mean)
        if index >= window - 1:
            results.append(WindowMoments(mean, sqrt(max(scatter, 0.0) / (window - 1))))
    return results


def _rolling_extreme(
    values: Sequence[float], window: int, dominates: Callable[[float, float], bool]
) -> list[float]:
    _require_window(window)
    candidates: deque[int] = deque()
    results: list[float] = []
    for index, value in enumerate(values):
        while candidates and dominates(value, values[candidates[-1]]):
            candidates.pop()
        candidates.append(index)
        if candidates[0] <= index - window:
            candidates.popleft()
        if index >= window - 1:
            results.append(values[candidates[0]])
    return results


def rolling_min(values: Sequence[float], window: int) -> list[float]:
    return _rolling_extreme(values, window, le)


def rolling_max(values: Sequence[float], window: int) -> list[float]:
    return _rolling_extreme(values, window, ge)
