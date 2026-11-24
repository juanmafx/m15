import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from m15.domain.candle import Candle


@dataclass(frozen=True, slots=True)
class Gap:
    last_before: datetime
    first_after: datetime
    missing_bars: int


def count_irregular_intervals(candles: Sequence[Candle], step: timedelta) -> int:
    return sum(
        1
        for previous, current in itertools.pairwise(candles)
        if (current.opened_at - previous.opened_at) % step
    )


def find_gaps(candles: Sequence[Candle], step: timedelta) -> list[Gap]:
    if step <= timedelta(0):
        raise ValueError("step must be positive")
    return [
        Gap(
            previous.opened_at,
            current.opened_at,
            (current.opened_at - previous.opened_at) // step - 1,
        )
        for previous, current in itertools.pairwise(candles)
        if current.opened_at - previous.opened_at > step
    ]
