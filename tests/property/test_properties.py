from math import isclose
from statistics import mean, stdev

from hypothesis import given
from hypothesis import strategies as st

from m15.analytics.drawdown import max_drawdown
from m15.analytics.gaps import find_gaps
from m15.analytics.resample import resample
from m15.analytics.rolling import rolling_max, rolling_min, rolling_moments
from m15.analytics.volatility import garman_klass, parkinson, rogers_satchell
from m15.data.metatrader_csv import format_series, parse_lines
from tests.strategies import STEP, candle_series, finite_values, prices


@given(st.lists(finite_values, min_size=2, max_size=80), st.integers(min_value=2, max_value=12))
def test_rolling_moments_match_direct_computation(values: list[float], window: int) -> None:
    results = rolling_moments(values, window)
    assert len(results) == max(len(values) - window + 1, 0)
    for offset, item in enumerate(results):
        sample = values[offset : offset + window]
        assert isclose(item.mean, mean(sample), rel_tol=1e-6, abs_tol=1e-6)
        assert isclose(item.std, stdev(sample), rel_tol=1e-3, abs_tol=1e-3)


@given(st.lists(finite_values, max_size=80), st.integers(min_value=1, max_value=12))
def test_rolling_extrema_match_direct_computation(values: list[float], window: int) -> None:
    spans = [values[i : i + window] for i in range(len(values) - window + 1)]
    assert rolling_min(values, window) == [min(span) for span in spans]
    assert rolling_max(values, window) == [max(span) for span in spans]


@given(st.lists(prices, min_size=1, max_size=60))
def test_max_drawdown_matches_quadratic_search(series: list[float]) -> None:
    expected = max(
        (1 - series[j] / series[i] for i in range(len(series)) for j in range(i, len(series))),
        default=0.0,
    )
    result = max_drawdown(series)
    assert isclose(result.depth, expected, abs_tol=1e-12)
    assert result.peak_index <= result.trough_index


@given(candle_series(), st.sampled_from([(30, 60), (60, 240), (15, 60), (240, 1440)]))
def test_resampling_composes(series, widths) -> None:
    fine, coarse = widths
    assert resample(resample(series, fine), coarse) == resample(series, coarse)


@given(candle_series(), st.sampled_from([30, 60, 240, 1440]))
def test_resampling_conserves_volume_and_extremes(series, minutes) -> None:
    aggregated = resample(series, minutes)
    assert sum(c.volume for c in aggregated) == sum(c.volume for c in series)
    assert max(c.high for c in aggregated) == max(c.high for c in series)
    assert min(c.low for c in aggregated) == min(c.low for c in series)
    assert aggregated[0].open == series[0].open
    assert aggregated[-1].close == series[-1].close


@given(candle_series())
def test_range_estimators_are_non_negative(series) -> None:
    assert parkinson(series) >= 0
    assert garman_klass(series) >= 0
    assert rogers_satchell(series) >= 0


@given(candle_series())
def test_gap_accounting_reconstructs_span(series) -> None:
    span = (series[-1].opened_at - series[0].opened_at) // STEP + 1
    assert len(series) + sum(gap.missing_bars for gap in find_gaps(series, STEP)) == span


@given(candle_series())
def test_csv_format_is_stable_after_first_round_trip(series) -> None:
    rounded = format_series(series, price_decimals=10).splitlines()
    parsed = parse_lines(rounded)
    assert format_series(parsed, price_decimals=10).splitlines() == rounded
