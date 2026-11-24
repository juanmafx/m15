from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import sqrt
from operator import ge, le

_Moments = tuple[int, float, float]


@dataclass(frozen=True, slots=True)
class WindowMoments:
    mean: float
    std: float


def _require_window(window: int) -> None:
    if window <= 0:
        raise ValueError("window must be positive")


def _merge(left: _Moments, right: _Moments) -> _Moments:
    left_count, left_mean, left_scatter = left
    right_count, right_mean, right_scatter = right
    count = left_count + right_count
    delta = right_mean - left_mean
    return (
        count,
        left_mean + delta * right_count / count,
        left_scatter + right_scatter + delta * delta * left_count * right_count / count,
    )


def rolling_moments(values: Sequence[float], window: int) -> list[WindowMoments]:
    _require_window(window)
    if window == 1:
        return [WindowMoments(value, 0.0) for value in values]
    if len(values) < window:
        return []
    suffixes: list[_Moments] = [(1, value, 0.0) for value in values]
    for index in range(len(values) - 2, -1, -1):
        if (index + 1) % window:
            suffixes[index] = _merge(suffixes[index], suffixes[index + 1])
    results: list[WindowMoments] = []
    prefix: _Moments = (1, values[0], 0.0)
    for index, value in enumerate(values):
        single: _Moments = (1, value, 0.0)
        prefix = single if index % window == 0 else _merge(prefix, single)
        if index < window - 1:
            continue
        start = index - window + 1
        combined = suffixes[start] if start % window == 0 else _merge(suffixes[start], prefix)
        results.append(WindowMoments(combined[1], sqrt(combined[2] / (window - 1))))
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
