import json
import re
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from importlib.resources import files
from pathlib import Path
from typing import Any

from m15.domain.candle import Candle

_SYMBOL = re.compile(r"[A-Z0-9._-]{1,32}")

_UPSERT_CANDLE = """
INSERT INTO candles (
    instrument_id, timeframe_minutes, opened_at,
    open_price, high_price, low_price, close_price, tick_volume
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (instrument_id, timeframe_minutes, opened_at) DO UPDATE SET
    open_price = excluded.open_price,
    high_price = excluded.high_price,
    low_price = excluded.low_price,
    close_price = excluded.close_price,
    tick_volume = excluded.tick_volume
"""

_INSERT_RUN = """
INSERT INTO analysis_runs (
    instrument_id, timeframe_minutes, window_bars, input_sha256, tool_version, report_json
) VALUES (?, ?, ?, ?, ?, ?)
"""


def schema_sql() -> str:
    return files("m15.storage").joinpath("schema.sql").read_text(encoding="utf-8")


def connect(database: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema_sql())
    return connection


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if not _SYMBOL.fullmatch(normalized):
        raise ValueError("symbol must be 1-32 characters of A-Z, 0-9, dot, underscore or dash")
    return normalized


def _instrument_id(connection: sqlite3.Connection, symbol: str) -> int:
    connection.execute(
        "INSERT INTO instruments (symbol) VALUES (?) ON CONFLICT (symbol) DO NOTHING", (symbol,)
    )
    row = connection.execute(
        "SELECT instrument_id FROM instruments WHERE symbol = ?", (symbol,)
    ).fetchone()
    return int(row[0])


def store_analysis(
    database: Path | str,
    symbol: str,
    timeframe_minutes: int,
    candles: Sequence[Candle],
    report: dict[str, Any],
) -> int:
    normalized = normalize_symbol(symbol)
    with closing(connect(database)) as connection, connection:
        instrument_id = _instrument_id(connection, normalized)
        connection.executemany(
            _UPSERT_CANDLE,
            (
                (
                    instrument_id,
                    timeframe_minutes,
                    candle.opened_at.isoformat(timespec="seconds"),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                )
                for candle in candles
            ),
        )
        cursor = connection.execute(
            _INSERT_RUN,
            (
                instrument_id,
                timeframe_minutes,
                report["parameters"]["window_bars"],
                report["input_sha256"],
                report["tool_version"],
                json.dumps(report, sort_keys=True),
            ),
        )
        return int(cursor.lastrowid or 0)
