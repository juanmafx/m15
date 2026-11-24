import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from m15.domain.candle import Candle
from m15.errors import CandleFormatError, CandleValidationError

MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_LINE_BYTES = 256
FIELD_COUNT = 7

_DATE = re.compile(r"[0-9]{4}\.[0-9]{2}\.[0-9]{2}")
_TIME = re.compile(r"[0-9]{2}:[0-9]{2}")
_PRICE = re.compile(r"[0-9]{1,12}(\.[0-9]{1,10})?")
_VOLUME = re.compile(r"[0-9]{1,15}")


@dataclass(frozen=True, slots=True)
class LoadedSeries:
    candles: tuple[Candle, ...]
    sha256: str


def parse_line(line: str, line_number: int) -> Candle:
    fields = line.split(",")
    if len(fields) != FIELD_COUNT:
        raise CandleFormatError(f"line {line_number}: expected {FIELD_COUNT} fields")
    date_text, time_text, *price_texts, volume_text = fields
    if not _DATE.fullmatch(date_text) or not _TIME.fullmatch(time_text):
        raise CandleFormatError(f"line {line_number}: invalid timestamp")
    if not all(_PRICE.fullmatch(text) for text in price_texts):
        raise CandleFormatError(f"line {line_number}: invalid price")
    if not _VOLUME.fullmatch(volume_text):
        raise CandleFormatError(f"line {line_number}: invalid volume")
    try:
        opened_at = datetime.strptime(f"{date_text} {time_text}", "%Y.%m.%d %H:%M")
        open_price, high, low, close = (float(text) for text in price_texts)
        return Candle(opened_at, open_price, high, low, close, int(volume_text))
    except (ValueError, CandleValidationError) as error:
        raise CandleFormatError(f"line {line_number}: {error}") from error


def parse_lines(lines: Iterable[str]) -> tuple[Candle, ...]:
    candles: list[Candle] = []
    for line_number, line in enumerate(lines, start=1):
        candle = parse_line(line.rstrip("\r\n"), line_number)
        if candles and candle.opened_at <= candles[-1].opened_at:
            raise CandleFormatError(f"line {line_number}: timestamps must strictly increase")
        candles.append(candle)
    return tuple(candles)


def read_series(path: Path, max_file_bytes: int = MAX_FILE_BYTES) -> LoadedSeries:
    if not path.is_file():
        raise CandleFormatError("input must be a regular file")
    digest = hashlib.sha256()
    lines: list[str] = []
    total_bytes = 0
    with path.open("rb") as handle:
        while raw_line := handle.readline(MAX_LINE_BYTES + 1):
            if len(raw_line) > MAX_LINE_BYTES:
                raise CandleFormatError(f"line {len(lines) + 1}: line too long")
            total_bytes += len(raw_line)
            if total_bytes > max_file_bytes:
                raise CandleFormatError("input exceeds the size limit")
            digest.update(raw_line)
            try:
                lines.append(raw_line.decode("ascii"))
            except UnicodeDecodeError as error:
                raise CandleFormatError(f"line {len(lines) + 1}: non-ASCII data") from error
    return LoadedSeries(parse_lines(lines), digest.hexdigest())


def format_candle(candle: Candle, price_decimals: int = 2) -> str:
    prices = ",".join(
        f"{price:.{price_decimals}f}"
        for price in (candle.open, candle.high, candle.low, candle.close)
    )
    stamp = candle.opened_at.strftime("%Y.%m.%d,%H:%M")
    return f"{stamp},{prices},{candle.volume}"


def format_series(candles: Iterable[Candle], price_decimals: int = 2) -> str:
    return "".join(f"{format_candle(candle, price_decimals)}\n" for candle in candles)
