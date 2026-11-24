from datetime import datetime, timedelta
from math import exp, isclose, log, sqrt

import pytest

from m15.analytics.drawdown import max_drawdown
from m15.analytics.gaps import find_gaps
from m15.analytics.report import build_report
from m15.analytics.resample import bucket_start, resample
from m15.analytics.returns import contiguous_log_returns, log_returns
from m15.analytics.rolling import rolling_max, rolling_min, rolling_moments
from m15.analytics.volatility import (
    annualize,
    close_to_close,
    garman_klass,
    parkinson,
    rogers_satchell,
)
from m15.data.synthetic import SimulationConfig, simulate_candles
from m15.domain.candle import Candle
from m15.errors import InsufficientDataError

STEP = timedelta(minutes=15)
START = datetime(2026, 1, 1)


def bar(offset: int, open_price: float, high: float, low: float, close: float) -> Candle:
    return Candle(START + STEP * offset, open_price, high, low, close, 10)


def test_log_returns_known_values() -> None:
    assert log_returns([1.0, exp(1.0)]) == pytest.approx([1.0])


def test_contiguous_returns_skip_gaps() -> None:
    series = [bar(0, 1, 1, 1, 1), bar(1, 2, 2, 2, 2), bar(5, 4, 4, 4, 4), bar(6, 8, 8, 8, 8)]
    assert contiguous_log_returns(series, STEP) == pytest.approx([log(2), log(2)])


def test_gaps_report_missing_bars() -> None:
    series = [bar(0, 1, 1, 1, 1), bar(1, 1, 1, 1, 1), bar(5, 1, 1, 1, 1)]
    gaps = find_gaps(series, STEP)
    assert [gap.missing_bars for gap in gaps] == [3]


def test_gaps_reject_invalid_step() -> None:
    with pytest.raises(ValueError, match="positive"):
        find_gaps([], timedelta(0))


def test_rolling_moments_known_values() -> None:
    result = rolling_moments([1.0, 2.0, 3.0, 4.0], 2)
    assert [item.mean for item in result] == pytest.approx([1.5, 2.5, 3.5])
    assert [item.std for item in result] == pytest.approx([sqrt(0.5)] * 3)


def test_rolling_window_of_one() -> None:
    assert [item.std for item in rolling_moments([3.0, 4.0], 1)] == [0.0, 0.0]


@pytest.mark.parametrize("function", [rolling_moments, rolling_min, rolling_max])
def test_rolling_rejects_invalid_window(function) -> None:
    with pytest.raises(ValueError, match="positive"):
        function([1.0], 0)


def test_rolling_extrema_known_values() -> None:
    values = [3.0, 1.0, 2.0, 5.0, 4.0]
    assert rolling_min(values, 3) == [1.0, 1.0, 2.0]
    assert rolling_max(values, 3) == [3.0, 5.0, 5.0]


def test_max_drawdown_known_values() -> None:
    result = max_drawdown([100.0, 120.0, 90.0, 110.0, 60.0, 200.0])
    assert result.depth == pytest.approx(0.5)
    assert (result.peak_index, result.trough_index) == (1, 4)


def test_max_drawdown_monotonic_series_is_zero() -> None:
    assert max_drawdown([1.0, 2.0, 3.0]).depth == 0.0


def test_max_drawdown_requires_data() -> None:
    with pytest.raises(InsufficientDataError):
        max_drawdown([])


def test_range_estimators_known_values() -> None:
    candle = bar(0, 100.0, 100.0 * exp(0.02), 100.0 * exp(-0.02), 100.0)
    assert parkinson([candle]) == pytest.approx(0.04 / sqrt(4 * log(2)))
    assert garman_klass([candle]) == pytest.approx(sqrt(0.5) * 0.04)
    assert rogers_satchell([candle]) == pytest.approx(sqrt(2 * 0.02**2))


@pytest.mark.parametrize("estimator", [parkinson, garman_klass, rogers_satchell])
def test_range_estimators_require_data(estimator) -> None:
    with pytest.raises(InsufficientDataError):
        estimator([])


def test_close_to_close_requires_two_returns() -> None:
    with pytest.raises(InsufficientDataError):
        close_to_close([0.1])


def test_annualize() -> None:
    assert isclose(annualize(0.01, 10_000), 1.0)
    with pytest.raises(ValueError, match="positive"):
        annualize(0.01, 0)


def test_bucket_start_aligns_to_epoch() -> None:
    assert bucket_start(datetime(2018, 3, 15, 7, 45), 60) == datetime(2018, 3, 15, 7, 0)


def test_resample_aggregates_ohlcv() -> None:
    series = [bar(0, 10, 12, 9, 11), bar(1, 11, 15, 10, 14), bar(4, 14, 14, 13, 13)]
    hourly = resample(series, 60)
    assert len(hourly) == 2
    first = hourly[0]
    assert (first.open, first.high, first.low, first.close, first.volume) == (10, 15, 9, 14, 20)


def test_resample_rejects_invalid_minutes() -> None:
    with pytest.raises(ValueError, match="positive"):
        resample([], 0)


def test_report_structure_and_gap_accounting() -> None:
    candles = list(simulate_candles(SimulationConfig(bars=300, seed=7)))
    del candles[100:110]
    report = build_report(candles, "0" * 64, window=48)
    assert report["coverage"]["bars"] == 290
    assert report["coverage"]["gap_count"] == 1
    assert report["coverage"]["missing_bars"] == 10
    assert report["coverage"]["contiguous_returns"] == 288
    assert all(value > 0 for value in report["annualized_volatility"].values())


@pytest.mark.parametrize(
    ("window", "timeframe", "error"),
    [(1, 15, ValueError), (2, 0, ValueError), (500, 15, InsufficientDataError)],
)
def test_report_rejects_invalid_parameters(
    window: int, timeframe: int, error: type[Exception]
) -> None:
    candles = simulate_candles(SimulationConfig(bars=50, seed=1))
    with pytest.raises(error):
        build_report(candles, "0" * 64, window=window, timeframe_minutes=timeframe)


@pytest.mark.parametrize(
    "changes",
    [
        {"bars": -1},
        {"initial_price": 0.0},
        {"annual_volatility": -0.1},
        {"timeframe_minutes": 0},
        {"substeps": 0},
        {"mean_volume": 0.0},
        {"annual_drift": float("inf")},
    ],
)
def test_simulation_rejects_invalid_configuration(changes: dict[str, float]) -> None:
    with pytest.raises(ValueError, match=r"must be"):
        SimulationConfig(**{"bars": 1, "seed": 1, **changes})
