import hashlib
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from m15.data.metatrader_csv import (
    MAX_LINE_BYTES,
    format_candle,
    format_series,
    parse_line,
    parse_lines,
    read_series,
)
from m15.errors import CandleFormatError

LINE = "2018.03.15,07:15,7872.78,7878.60,7781.18,7823.85,499"
NEXT_LINE = "2018.03.15,07:30,7823.90,7869.70,7822.99,7839.59,536"


def test_parses_a_valid_line() -> None:
    candle = parse_line(LINE, 1)
    assert candle.opened_at == datetime(2018, 3, 15, 7, 15)
    assert (candle.open, candle.high, candle.low, candle.close) == (
        7872.78,
        7878.60,
        7781.18,
        7823.85,
    )
    assert candle.volume == 499


@pytest.mark.parametrize(
    "line",
    [
        "",
        "2018.03.15,07:15,1,2,0.5,1",
        "2018-03-15,07:15,1,2,0.5,1,3",
        "2018.13.15,07:15,1,2,0.5,1,3",
        "2018.03.15,25:15,1,2,0.5,1,3",
        "2018.03.15,07:15,nan,2,0.5,1,3",
        "2018.03.15,07:15,1e5,2,0.5,1,3",
        "2018.03.15,07:15,-1,2,0.5,1,3",
        "2018.03.15,07:15,1,2,0.5,1,-3",
        "2018.03.15,07:15,1,2,0.5,1,3.5",
        "2018.03.15,07:15,1,0.9,0.5,1,3",
        "=cmd(),07:15,1,2,0.5,1,3",
    ],
)
def test_rejects_malformed_lines(line: str) -> None:
    with pytest.raises(CandleFormatError):
        parse_line(line, 1)


@pytest.mark.parametrize("lines", [[NEXT_LINE, LINE], [LINE, LINE]])
def test_rejects_non_increasing_timestamps(lines: list[str]) -> None:
    with pytest.raises(CandleFormatError, match="strictly increase"):
        parse_lines(lines)


def test_read_series_hashes_exact_bytes(tmp_path: Path) -> None:
    content = f"{LINE}\r\n{NEXT_LINE}\n".encode("ascii")
    path = tmp_path / "bars.csv"
    path.write_bytes(content)
    series = read_series(path)
    assert len(series.candles) == 2
    assert series.sha256 == hashlib.sha256(content).hexdigest()


def test_read_series_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(CandleFormatError, match="regular file"):
        read_series(tmp_path)


def test_read_series_rejects_long_line(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_bytes(b"1" * (MAX_LINE_BYTES + 1))
    with pytest.raises(CandleFormatError, match="too long"):
        read_series(path)


def test_read_series_enforces_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_text(f"{LINE}\n", encoding="ascii")
    with pytest.raises(CandleFormatError, match="size limit"):
        read_series(path, max_file_bytes=4)


def test_read_series_rejects_non_ascii(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_bytes(b"2018.03.15,07:15,1,2,0.5,1,\xc3\xa9\n")
    with pytest.raises(CandleFormatError, match="non-ASCII"):
        read_series(path)


def test_read_series_rejects_empty_input(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_bytes(b"")
    with pytest.raises(CandleFormatError, match="no bars"):
        read_series(path)


def test_read_series_reports_widest_price_precision(tmp_path: Path) -> None:
    path = tmp_path / "bars.csv"
    path.write_text(
        "2026.01.05,00:00,1.2,1.23499,1,1.2,10\n2026.01.05,00:15,2,3,1,2,10\n", encoding="ascii"
    )
    assert read_series(path).price_decimals == 5


@pytest.mark.parametrize(
    ("line", "decimals"),
    [
        ("2026.01.05,00:00,0.001,0.002,0.001,0.001,1", 2),
        ("2026.01.05,00:00,999999999999,999999999999.9,999999999999,999999999999,1", 0),
    ],
)
def test_format_refuses_prices_the_file_format_cannot_hold(line: str, decimals: int) -> None:
    with pytest.raises(CandleFormatError, match="does not fit"):
        format_candle(parse_line(line, 1), decimals)


def test_format_refuses_volume_beyond_file_format() -> None:
    candle = replace(parse_line(LINE, 1), volume=10**15)
    with pytest.raises(CandleFormatError, match="15-digit"):
        format_candle(candle)


def test_format_round_trip() -> None:
    candles = parse_lines([LINE, NEXT_LINE])
    assert format_series(candles) == f"{LINE}\n{NEXT_LINE}\n"
