from collections.abc import Sequence
from datetime import timedelta
from math import fsum
from typing import Any

from m15 import __version__
from m15.analytics.drawdown import max_drawdown
from m15.analytics.gaps import count_irregular_intervals, find_gaps
from m15.analytics.returns import contiguous_log_returns
from m15.analytics.rolling import rolling_max, rolling_min, rolling_moments
from m15.analytics.volatility import (
    annualize,
    close_to_close,
    garman_klass,
    parkinson,
    rogers_satchell,
)
from m15.domain.candle import Candle
from m15.errors import InsufficientDataError

MINUTES_PER_YEAR = 365 * 24 * 60


def build_report(
    candles: Sequence[Candle],
    input_sha256: str,
    window: int = 96,
    timeframe_minutes: int = 15,
) -> dict[str, Any]:
    if timeframe_minutes <= 0:
        raise ValueError("timeframe_minutes must be positive")
    if window < 2:
        raise ValueError("window must be at least 2")
    step = timedelta(minutes=timeframe_minutes)
    returns = contiguous_log_returns(candles, step)
    if len(returns) < window:
        raise InsufficientDataError("not enough contiguous returns for the requested window")
    bars_per_year = MINUTES_PER_YEAR / timeframe_minutes
    closes = [candle.close for candle in candles]
    gaps = find_gaps(candles, step)
    drawdown = max_drawdown(closes)
    latest_moments = rolling_moments(returns, window)[-1]
    estimators = {
        "close_to_close": close_to_close(returns),
        "parkinson": parkinson(candles),
        "garman_klass": garman_klass(candles),
        "rogers_satchell": rogers_satchell(candles),
    }
    return {
        "tool_version": __version__,
        "input_sha256": input_sha256,
        "parameters": {
            "window_bars": window,
            "timeframe_minutes": timeframe_minutes,
            "bars_per_year": bars_per_year,
        },
        "coverage": {
            "bars": len(candles),
            "first_bar": candles[0].opened_at.isoformat(),
            "last_bar": candles[-1].opened_at.isoformat(),
            "gap_count": len(gaps),
            "missing_bars": sum(gap.missing_bars for gap in gaps),
            "irregular_intervals": count_irregular_intervals(candles, step),
            "contiguous_returns": len(returns),
        },
        "returns": {
            "mean": fsum(returns) / len(returns),
            "minimum": min(returns),
            "maximum": max(returns),
        },
        "annualized_volatility": {
            name: annualize(value, bars_per_year) for name, value in estimators.items()
        },
        "max_drawdown": {
            "depth": drawdown.depth,
            "peak_bar": candles[drawdown.peak_index].opened_at.isoformat(),
            "trough_bar": candles[drawdown.trough_index].opened_at.isoformat(),
        },
        "latest_window": {
            "return_mean": latest_moments.mean,
            "return_std": latest_moments.std,
            "close_minimum": rolling_min(closes, window)[-1],
            "close_maximum": rolling_max(closes, window)[-1],
        },
    }
