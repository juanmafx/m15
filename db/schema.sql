-- Optional SQLite persistence for M15 candles and analysis runs.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS instruments (
    instrument_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE CHECK (length(symbol) BETWEEN 1 AND 32)
) STRICT;

CREATE TABLE IF NOT EXISTS candles (
    instrument_id INTEGER NOT NULL REFERENCES instruments (instrument_id) ON DELETE CASCADE,
    timeframe_minutes INTEGER NOT NULL CHECK (timeframe_minutes > 0),
    opened_at TEXT NOT NULL CHECK (opened_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]'),
    open_price REAL NOT NULL CHECK (open_price > 0),
    high_price REAL NOT NULL,
    low_price REAL NOT NULL CHECK (low_price > 0),
    close_price REAL NOT NULL CHECK (close_price > 0),
    tick_volume INTEGER NOT NULL CHECK (tick_volume >= 0),
    PRIMARY KEY (instrument_id, timeframe_minutes, opened_at),
    CHECK (high_price >= open_price AND high_price >= close_price AND high_price >= low_price),
    CHECK (low_price <= open_price AND low_price <= close_price)
) STRICT, WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL REFERENCES instruments (instrument_id) ON DELETE CASCADE,
    timeframe_minutes INTEGER NOT NULL CHECK (timeframe_minutes > 0),
    window_bars INTEGER NOT NULL CHECK (window_bars >= 2),
    input_sha256 TEXT NOT NULL CHECK (length(input_sha256) = 64),
    tool_version TEXT NOT NULL,
    report_json TEXT NOT NULL CHECK (json_valid(report_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
) STRICT;

CREATE INDEX IF NOT EXISTS analysis_runs_by_input ON analysis_runs (input_sha256, created_at);
