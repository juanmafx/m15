import hashlib
from math import sqrt
from statistics import NormalDist, fmean, stdev

import pytest

from m15.analytics.returns import log_returns
from m15.analytics.volatility import garman_klass, parkinson, rogers_satchell
from m15.data.metatrader_csv import format_series
from m15.data.synthetic import MINUTES_PER_YEAR, SimulationConfig, simulate_candles

BARS = 20_000
SEED = 20260101
KOLMOGOROV_CRITICAL_ONE_PERCENT = 1.628
Z_CRITICAL = 3.29
CONFIG = SimulationConfig(bars=BARS, seed=SEED)
BAR_YEARS = CONFIG.timeframe_minutes / MINUTES_PER_YEAR
SIGMA_PER_BAR = CONFIG.annual_volatility * sqrt(BAR_YEARS)
MU_PER_BAR = (CONFIG.annual_drift - CONFIG.annual_volatility**2 / 2) * BAR_YEARS


@pytest.fixture(scope="module")
def candles():
    return simulate_candles(CONFIG)


@pytest.fixture(scope="module")
def returns(candles):
    closes = [CONFIG.initial_price, *(candle.close for candle in candles)]
    return log_returns(closes)


def test_same_seed_is_identical(candles) -> None:
    assert simulate_candles(SimulationConfig(bars=BARS, seed=SEED)) == candles


def test_different_seed_differs() -> None:
    first = simulate_candles(SimulationConfig(bars=10, seed=1))
    second = simulate_candles(SimulationConfig(bars=10, seed=2))
    assert first != second


def test_golden_digest_detects_generator_changes() -> None:
    text = format_series(simulate_candles(SimulationConfig(bars=256, seed=42)), price_decimals=6)
    assert hashlib.sha256(text.encode("ascii")).hexdigest() == GOLDEN_DIGEST


def test_mean_log_return_matches_theory(returns) -> None:
    standard_error = SIGMA_PER_BAR / sqrt(len(returns))
    assert abs(fmean(returns) - MU_PER_BAR) < Z_CRITICAL * standard_error


def test_return_volatility_matches_theory(returns) -> None:
    standard_error = SIGMA_PER_BAR / sqrt(2 * (len(returns) - 1))
    assert abs(stdev(returns) - SIGMA_PER_BAR) < Z_CRITICAL * standard_error


def test_returns_pass_kolmogorov_smirnov(returns) -> None:
    distribution = NormalDist(MU_PER_BAR, SIGMA_PER_BAR)
    ordered = sorted(returns)
    size = len(ordered)
    statistic = max(
        max((rank + 1) / size - distribution.cdf(value), distribution.cdf(value) - rank / size)
        for rank, value in enumerate(ordered)
    )
    assert statistic < KOLMOGOROV_CRITICAL_ONE_PERCENT / sqrt(size)


@pytest.mark.parametrize("estimator", [parkinson, garman_klass, rogers_satchell])
def test_range_estimators_converge_as_monitoring_gets_finer(estimator) -> None:
    coarse = simulate_candles(SimulationConfig(bars=3_000, seed=SEED, substeps=32))
    fine = simulate_candles(SimulationConfig(bars=3_000, seed=SEED, substeps=512))
    coarse_bias = estimator(coarse) / SIGMA_PER_BAR - 1
    fine_bias = estimator(fine) / SIGMA_PER_BAR - 1
    assert coarse_bias < fine_bias < 0
    assert abs(fine_bias) < 0.06


def test_prices_stay_positive(candles) -> None:
    assert all(candle.low > 0 for candle in candles)


def test_volume_mean_is_close_to_configured(candles) -> None:
    assert fmean(candle.volume for candle in candles) == pytest.approx(CONFIG.mean_volume, rel=0.02)


GOLDEN_DIGEST = "d250c3bf653770e22123e15ea38b5ab0a6e3e219789787713f82a1f94fbde0ba"
