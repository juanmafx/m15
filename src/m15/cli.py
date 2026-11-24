import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from m15 import __version__
from m15.analytics.report import build_report
from m15.analytics.resample import resample
from m15.data.metatrader_csv import format_series, read_series
from m15.data.synthetic import SimulationConfig, simulate_candles
from m15.errors import M15Error
from m15.legacy.python_docs_csv import write_example
from m15.storage.files import write_text_atomic
from m15.storage.sqlite_repository import store_analysis

MAX_SIMULATED_BARS = 5_000_000


def _positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _bar_count(text: str) -> int:
    value = _positive_int(text)
    if value > MAX_SIMULATED_BARS:
        raise argparse.ArgumentTypeError(f"must be at most {MAX_SIMULATED_BARS}")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m15", description="Analyze 15-minute OHLCV bars.")
    parser.add_argument("--version", action="version", version=f"m15 {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    simulate = commands.add_parser("simulate", help="generate a seeded synthetic series")
    simulate.add_argument("--bars", type=_bar_count, required=True)
    simulate.add_argument("--seed", type=int, required=True)
    simulate.add_argument("--start", type=datetime.fromisoformat, default=datetime(2026, 1, 1))
    simulate.add_argument("--initial-price", type=float, default=100.0)
    simulate.add_argument("--annual-drift", type=float, default=0.05)
    simulate.add_argument("--annual-volatility", type=float, default=0.60)
    simulate.add_argument("--output", type=Path, required=True)
    simulate.add_argument("--force", action="store_true")

    analyze = commands.add_parser("analyze", help="print a JSON analysis report")
    analyze.add_argument("input", type=Path)
    analyze.add_argument("--window", type=_positive_int, default=96)
    analyze.add_argument("--timeframe-minutes", type=_positive_int, default=15)
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--force", action="store_true")
    analyze.add_argument("--database", type=Path)
    analyze.add_argument("--symbol", default="BTCUSD")

    resample_command = commands.add_parser("resample", help="aggregate to a larger timeframe")
    resample_command.add_argument("input", type=Path)
    resample_command.add_argument("--minutes", type=_positive_int, required=True)
    resample_command.add_argument("--output", type=Path, required=True)
    resample_command.add_argument("--force", action="store_true")

    example = commands.add_parser("csv-example", help="write the original csv exercise output")
    example.add_argument("--output", type=Path, required=True)
    return parser


def _simulate(arguments: argparse.Namespace) -> None:
    config = SimulationConfig(
        bars=arguments.bars,
        seed=arguments.seed,
        start=arguments.start,
        initial_price=arguments.initial_price,
        annual_drift=arguments.annual_drift,
        annual_volatility=arguments.annual_volatility,
    )
    write_text_atomic(
        arguments.output, format_series(simulate_candles(config)), overwrite=arguments.force
    )


def _analyze(arguments: argparse.Namespace) -> None:
    series = read_series(arguments.input)
    report = build_report(
        series.candles, series.sha256, arguments.window, arguments.timeframe_minutes
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        write_text_atomic(arguments.output, rendered, overwrite=arguments.force)
    if arguments.database is not None:
        store_analysis(
            arguments.database,
            arguments.symbol,
            arguments.timeframe_minutes,
            series.candles,
            report,
        )
    if arguments.output is None:
        sys.stdout.write(rendered)


def _resample(arguments: argparse.Namespace) -> None:
    series = read_series(arguments.input)
    write_text_atomic(
        arguments.output,
        format_series(resample(series.candles, arguments.minutes)),
        overwrite=arguments.force,
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "simulate":
            _simulate(arguments)
        elif arguments.command == "analyze":
            _analyze(arguments)
        elif arguments.command == "resample":
            _resample(arguments)
        else:
            write_example(arguments.output)
    except (M15Error, ValueError, OSError, OverflowError, sqlite3.Error) as error:
        message = error.strerror if isinstance(error, OSError) and error.strerror else error
        print(f"error: {message}", file=sys.stderr)
        return 2
    return 0
