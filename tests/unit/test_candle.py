from dataclasses import replace
from datetime import UTC, datetime

import pytest

from m15.domain.candle import Candle
from m15.errors import CandleValidationError

VALID = Candle(datetime(2026, 1, 1), 10.0, 12.0, 9.0, 11.0, 5)


@pytest.mark.parametrize(
    "changes",
    [
        {"open": 0.0},
        {"close": -1.0},
        {"open": float("nan")},
        {"high": float("inf")},
        {"high": 10.5},
        {"low": 10.5},
        {"volume": -1},
        {"opened_at": datetime(2026, 1, 1, tzinfo=UTC)},
    ],
)
def test_rejects_invalid_candles(changes: dict[str, object]) -> None:
    with pytest.raises(CandleValidationError):
        replace(VALID, **changes)


def test_accepts_flat_candle() -> None:
    assert Candle(VALID.opened_at, 5.0, 5.0, 5.0, 5.0, 0).high == 5.0


def test_rejects_all_zero_prices() -> None:
    with pytest.raises(CandleValidationError):
        Candle(VALID.opened_at, 0.0, 0.0, 0.0, 0.0, 0)
