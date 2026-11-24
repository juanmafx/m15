from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from m15.errors import CandleValidationError


@dataclass(frozen=True, slots=True)
class Candle:
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is not None:
            raise CandleValidationError("opened_at must be a naive timestamp")
        prices = (self.open, self.high, self.low, self.close)
        if not all(isfinite(price) and price > 0 for price in prices):
            raise CandleValidationError("prices must be finite and positive")
        if self.high < max(self.open, self.close, self.low):
            raise CandleValidationError("high must be the largest price")
        if self.low > min(self.open, self.close, self.high):
            raise CandleValidationError("low must be the smallest price")
        if self.volume < 0:
            raise CandleValidationError("volume must be non-negative")
