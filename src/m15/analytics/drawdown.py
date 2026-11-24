from collections.abc import Sequence
from dataclasses import dataclass

from m15.errors import InsufficientDataError


@dataclass(frozen=True, slots=True)
class Drawdown:
    depth: float
    peak_index: int
    trough_index: int


def max_drawdown(prices: Sequence[float]) -> Drawdown:
    if not prices:
        raise InsufficientDataError("at least one price is required")
    best = Drawdown(0.0, 0, 0)
    peak_index = 0
    for index, price in enumerate(prices):
        if price > prices[peak_index]:
            peak_index = index
        depth = 1 - price / prices[peak_index]
        if depth > best.depth:
            best = Drawdown(depth, peak_index, index)
    return best
