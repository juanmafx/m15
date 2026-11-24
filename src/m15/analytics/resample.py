from collections.abc import Sequence
from datetime import datetime, timedelta
from itertools import groupby

from m15.domain.candle import Candle

_EPOCH = datetime(1970, 1, 1)


def bucket_start(moment: datetime, minutes: int) -> datetime:
    width = timedelta(minutes=minutes)
    return _EPOCH + ((moment - _EPOCH) // width) * width


def resample(
    candles: Sequence[Candle], minutes: int, source_minutes: int = 15
) -> tuple[Candle, ...]:
    if minutes <= 0 or source_minutes <= 0:
        raise ValueError("minutes must be positive")
    if minutes % source_minutes:
        raise ValueError("minutes must be a whole multiple of the source timeframe")
    source = timedelta(minutes=source_minutes)
    if any((candle.opened_at - _EPOCH) % source for candle in candles):
        raise ValueError("bars are not aligned to the source timeframe")
    aggregated: list[Candle] = []
    for start, members in groupby(candles, key=lambda c: bucket_start(c.opened_at, minutes)):
        bucket = tuple(members)
        aggregated.append(
            Candle(
                start,
                bucket[0].open,
                max(candle.high for candle in bucket),
                min(candle.low for candle in bucket),
                bucket[-1].close,
                sum(candle.volume for candle in bucket),
            )
        )
    return tuple(aggregated)
