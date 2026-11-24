import itertools
from collections.abc import Sequence
from datetime import timedelta
from math import log

from m15.domain.candle import Candle


def log_returns(closes: Sequence[float]) -> list[float]:
    return [log(current / previous) for previous, current in itertools.pairwise(closes)]


def contiguous_log_returns(candles: Sequence[Candle], step: timedelta) -> list[float]:
    return [
        log(current.close / previous.close)
        for previous, current in itertools.pairwise(candles)
        if current.opened_at - previous.opened_at == step
    ]
