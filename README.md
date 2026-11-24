# m15

A small, dependency-free Python toolkit for validating and analyzing 15-minute (M15) OHLCV market bars, with seeded simulation and statistical tests.

> **Project history:** originally created in 2018 as a short CSV exercise alongside a Bitcoin M15 export, modernized in 2026 into the toolkit described here. The commits from 2026 are new work.

## Purpose

Intraday price files are easy to misread: exports contain weekend gaps, malformed rows, and silently reordered bars, and a volatility figure computed across a gap is wrong. `m15` turns one such file into a checked series and a reproducible JSON report that records the exact input hash and parameters.

## Why this project exists

The 2018 repository held one script and a data file. The script was the `csv.writer` example from the Python documentation and no longer ran on Python 3. The question the data invited, what can be measured reliably from M15 bars, was never answered. This version answers it with correct estimators, explicit assumptions, and tests that check the mathematics.

## What it does

- Parses the headerless MetaTrader-style format `YYYY.MM.DD,HH:MM,open,high,low,close,volume` under strict validation.
- Detects gaps and excludes returns that span them.
- Computes close-to-close, Parkinson, Garman-Klass, and Rogers-Satchell volatility.
- Computes maximum drawdown and rolling mean, deviation, minimum, and maximum in linear time.
- Resamples to any larger timeframe.
- Simulates seeded geometric Brownian motion bars for reproducible experiments.
- Optionally stores candles and analysis runs in SQLite.

It is an analysis tool. It does not fetch market data, place orders, forecast prices, or give financial advice.

## Architecture

```text
src/m15/
  cli.py            command-line interface
  domain/           validated Candle value object
  data/             CSV parsing and seeded simulation
  analytics/        returns, rolling windows, volatility, drawdown, gaps, resampling, reports
  storage/          atomic file writes and SQLite persistence
  legacy/           the original exercise, ported and credited
db/schema.sql       optional SQLite schema
tests/              unit, property-based, and statistical suites
reports/tests/      committed report from a real test run
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design, algorithms, and complexity.

## Quick start

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/). The runtime has no third-party dependencies.

```bash
uv sync --locked
uv run m15 simulate --bars 2000 --seed 42 --output bars.csv
uv run m15 analyze bars.csv --window 96
```

## Usage guide

```bash
uv run m15 simulate --bars 5000 --seed 7 --annual-volatility 0.8 --output synthetic.csv
uv run m15 analyze synthetic.csv --window 96 --output report.json
uv run m15 resample synthetic.csv --minutes 60 --output hourly.csv
uv run m15 analyze synthetic.csv --database runs.sqlite3 --symbol SYNTH
uv run m15 csv-example --output eggs.csv
```

Output files are never overwritten unless `--force` is passed. Errors print to standard error and exit with status 2.

## Configuration

There are no environment variables or configuration files. All behavior is set by flags.

| Flag | Command | Default | Meaning |
| --- | --- | --- | --- |
| `--seed` | `simulate` | required | Random seed |
| `--bars` | `simulate` | required | Bars to generate, up to 5,000,000 |
| `--annual-drift` | `simulate` | `0.05` | Annual drift of the process |
| `--annual-volatility` | `simulate` | `0.60` | Annual volatility of the process |
| `--initial-price` | `simulate` | `100` | First open |
| `--start` | `simulate` | `2026-01-01` | First bar timestamp |
| `--window` | `analyze` | `96` | Rolling window in bars (one day of M15) |
| `--timeframe-minutes` | `analyze` | `15` | Expected bar spacing |
| `--database` | `analyze` | none | SQLite file for persistence |
| `--symbol` | `analyze` | `BTCUSD` | Instrument label stored with the run |
| `--minutes` | `resample` | required | Target timeframe |

Annualization assumes a market open all year (`365 * 24 * 60 / timeframe` bars). Timestamps are treated as naive because MetaTrader exports use broker server time. The seventh column is read as tick volume; the original export did not label it.

## Database

Persistence is optional. [db/schema.sql](db/schema.sql) defines `instruments`, `candles`, and `analysis_runs` as SQLite `STRICT` tables with integrity constraints.

```bash
sqlite3 m15.sqlite3 < db/schema.sql
```

## Testing

```bash
uv sync --locked
uv run python -m pytest --cov --cov-branch
```

The suite has three layers: unit tests, property-based tests with Hypothesis in a derandomized profile, and statistical tests that compare simulated output with theory, including a Kolmogorov-Smirnov test. The latest real run is in [reports/tests/summary.md](reports/tests/summary.md).

## Security

The tool takes local files only and makes no network calls. Input is size-limited and strictly validated, SQL is parameterized, and writes are atomic. See [SECURITY.md](SECURITY.md) and [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).

## Attribution and license

- `src/m15/legacy/python_docs_csv.py` and `tests/fixtures/python_docs_eggs.csv` derive from the `csv` module example in the [Python documentation](https://docs.python.org/3/library/csv.html), which is covered by the Python Software Foundation License.
- The Parkinson (1980), Garman-Klass (1980), and Rogers-Satchell (1991) estimators are published methods. References are in the architecture document.
- The repository does not declare a license, so default copyright applies to the original code.
