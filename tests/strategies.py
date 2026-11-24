from datetime import datetime, timedelta

from hypothesis import strategies as st

from m15.domain.candle import Candle

STEP = timedelta(minutes=15)
START = datetime(2018, 3, 15, 7, 15)

prices = st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False)
finite_values = st.floats(min_value=-1_000, max_value=1_000, allow_nan=False, allow_infinity=False)


@st.composite
def candles(draw: st.DrawFn, opened_at: datetime = START) -> Candle:
    quartet = sorted(draw(st.lists(prices, min_size=4, max_size=4)))
    low, first, second, high = quartet
    open_price, close = (first, second) if draw(st.booleans()) else (second, first)
    volume = draw(st.integers(min_value=0, max_value=1_000_000))
    return Candle(opened_at, open_price, high, low, close, volume)


@st.composite
def candle_series(draw: st.DrawFn, min_size: int = 1, max_size: int = 60) -> tuple[Candle, ...]:
    skips = draw(
        st.lists(st.integers(min_value=1, max_value=9), min_size=min_size, max_size=max_size)
    )
    series = []
    moment = START
    for skip in skips:
        series.append(draw(candles(opened_at=moment)))
        moment += STEP * skip
    return tuple(series)
