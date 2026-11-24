from dataclasses import dataclass
from datetime import datetime, timedelta
from math import exp, isfinite, log, sqrt
from random import Random
from statistics import NormalDist

from m15.domain.candle import Candle

MINUTES_PER_YEAR = 365 * 24 * 60
_STANDARD_NORMAL = NormalDist()
_SMALLEST_UNIFORM = 2.0**-53


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    bars: int
    seed: int
    start: datetime = datetime(2026, 1, 1)
    initial_price: float = 100.0
    annual_drift: float = 0.05
    annual_volatility: float = 0.60
    timeframe_minutes: int = 15
    substeps: int = 32
    mean_volume: float = 400.0

    def __post_init__(self) -> None:
        parameters = (
            self.initial_price,
            self.annual_drift,
            self.annual_volatility,
            self.mean_volume,
        )
        if not all(isfinite(parameter) for parameter in parameters):
            raise ValueError("simulation parameters must be finite")
        if self.bars < 0:
            raise ValueError("bars must be non-negative")
        if self.initial_price <= 0:
            raise ValueError("initial_price must be positive")
        if self.annual_volatility < 0:
            raise ValueError("annual_volatility must be non-negative")
        if self.timeframe_minutes <= 0:
            raise ValueError("timeframe_minutes must be positive")
        if self.substeps <= 0:
            raise ValueError("substeps must be positive")
        if self.mean_volume <= 0:
            raise ValueError("mean_volume must be positive")


def _standard_normal(rng: Random) -> float:
    return _STANDARD_NORMAL.inv_cdf(max(rng.random(), _SMALLEST_UNIFORM))


def simulate_candles(config: SimulationConfig) -> tuple[Candle, ...]:
    rng = Random(config.seed)
    step_years = config.timeframe_minutes / MINUTES_PER_YEAR / config.substeps
    variance = config.annual_volatility**2
    drift_step = (config.annual_drift - variance / 2) * step_years
    diffusion_step = config.annual_volatility * sqrt(step_years)
    volume_sigma = 0.5
    volume_mu = log(config.mean_volume) - volume_sigma**2 / 2
    log_price = log(config.initial_price)
    candles: list[Candle] = []
    for index in range(config.bars):
        log_open = log_high = log_low = log_price
        for _ in range(config.substeps):
            log_price += drift_step + diffusion_step * _standard_normal(rng)
            log_high = max(log_high, log_price)
            log_low = min(log_low, log_price)
        open_price, close = exp(log_open), exp(log_price)
        volume = round(exp(volume_mu + volume_sigma * _standard_normal(rng)))
        candles.append(
            Candle(
                config.start + timedelta(minutes=config.timeframe_minutes * index),
                open_price,
                max(exp(log_high), open_price, close),
                min(exp(log_low), open_price, close),
                close,
                volume,
            )
        )
    return tuple(candles)
