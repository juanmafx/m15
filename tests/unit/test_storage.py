import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from m15.analytics.report import build_report
from m15.data.synthetic import SimulationConfig, simulate_candles
from m15.storage.files import write_text_atomic
from m15.storage.sqlite_repository import (
    connect,
    normalize_symbol,
    schema_sql,
    store_analysis,
)

ROOT = Path(__file__).resolve().parents[2]


def test_public_schema_matches_packaged_schema() -> None:
    assert (ROOT / "db" / "schema.sql").read_text(encoding="utf-8") == schema_sql()


def test_store_is_idempotent_for_candles(tmp_path: Path) -> None:
    candles = simulate_candles(SimulationConfig(bars=120, seed=3))
    report = build_report(candles, "a" * 64, window=24)
    database = tmp_path / "m15.sqlite3"
    first = store_analysis(database, "btcusd", 15, candles, report)
    second = store_analysis(database, "BTCUSD", 15, candles, report)
    assert second == first + 1
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM candles").fetchone() == (120,)
        assert connection.execute("SELECT count(*) FROM instruments").fetchone() == (1,)
        stored = connection.execute("SELECT report_json FROM analysis_runs").fetchone()[0]
    assert json.loads(stored)["input_sha256"] == "a" * 64


@pytest.mark.parametrize("symbol", ["", "BTC USD", "x'; DROP TABLE candles; --", "A" * 33])
def test_rejects_unsafe_symbols(symbol: str) -> None:
    with pytest.raises(ValueError, match="symbol"):
        normalize_symbol(symbol)


def test_schema_enforces_ohlc_constraints(tmp_path: Path) -> None:
    with closing(connect(tmp_path / "m15.sqlite3")) as connection:
        connection.execute("INSERT INTO instruments (symbol) VALUES ('X')")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO candles VALUES (1, 15, '2026-01-01T00:00:00', 10, 9, 8, 10, 1)"
            )


def test_schema_enforces_foreign_keys(tmp_path: Path) -> None:
    with (
        closing(connect(tmp_path / "m15.sqlite3")) as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute(
            "INSERT INTO candles VALUES (99, 15, '2026-01-01T00:00:00', 10, 11, 9, 10, 1)"
        )


def test_atomic_write_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    write_text_atomic(path, "first")
    with pytest.raises(FileExistsError):
        write_text_atomic(path, "second")
    assert path.read_text(encoding="utf-8") == "first"
    assert [item.name for item in tmp_path.iterdir()] == ["out.txt"]


def test_atomic_write_overwrites_when_forced(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    write_text_atomic(path, "first")
    write_text_atomic(path, "second", overwrite=True)
    assert path.read_text(encoding="utf-8") == "second"


def test_forced_write_replaces_symlink_not_target(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("keep", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    write_text_atomic(link, "new", overwrite=True)
    assert target.read_text(encoding="utf-8") == "keep"
    assert not link.is_symlink()
