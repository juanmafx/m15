from collections.abc import Sequence
from math import fsum, log, sqrt
from statistics import stdev

from m15.domain.candle import Candle
from m15.errors import InsufficientDataError

_GARMAN_KLASS_CLOSE_WEIGHT = 2 * log(2) - 1


def _require_candles(candles: Sequence[Candle]) -> None:
    if not candles:
        raise InsufficientDataError("at least one candle is required")


def close_to_close(returns: Sequence[float]) -> float:
    if len(returns) < 2:
        raise InsufficientDataError("at least two returns are required")
    return stdev(returns)


def parkinson(candles: Sequence[Candle]) -> float:
    _require_candles(candles)
    total = fsum(log(candle.high / candle.low) ** 2 for candle in candles)
    return sqrt(total / (4 * log(2) * len(candles)))


def garman_klass(candles: Sequence[Candle]) -> float:
    _require_candles(candles)
    total = fsum(
        0.5 * log(candle.high / candle.low) ** 2
        - _GARMAN_KLASS_CLOSE_WEIGHT * log(candle.close / candle.open) ** 2
        for candle in candles
    )
    return sqrt(max(total, 0.0) / len(candles))


def rogers_satchell(candles: Sequence[Candle]) -> float:
    _require_candles(candles)
    total = fsum(
        log(candle.high / candle.close) * log(candle.high / candle.open)
        + log(candle.low / candle.close) * log(candle.low / candle.open)
        for candle in candles
    )
    return sqrt(max(total, 0.0) / len(candles))


def annualize(per_bar_volatility: float, bars_per_year: float) -> float:
    if bars_per_year <= 0:
        raise ValueError("bars_per_year must be positive")
    return per_bar_volatility * sqrt(bars_per_year)
