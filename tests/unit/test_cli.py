import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from m15 import __version__
from m15.cli import main

ROOT = Path(__file__).resolve().parents[2]


def simulate(path: Path, bars: int = 300, seed: int = 11) -> None:
    assert main(["simulate", "--bars", str(bars), "--seed", str(seed), "--output", str(path)]) == 0


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_simulate_is_reproducible(tmp_path: Path) -> None:
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    simulate(first)
    simulate(second)
    assert first.read_bytes() == second.read_bytes()


def test_simulate_refuses_existing_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "a.csv"
    simulate(path)
    assert main(["simulate", "--bars", "5", "--seed", "1", "--output", str(path)]) == 2
    assert "error" in capsys.readouterr().err


def test_simulate_rejects_non_finite_parameters(tmp_path: Path) -> None:
    arguments = ["simulate", "--bars", "5", "--seed", "1", "--output", str(tmp_path / "a.csv")]
    assert main([*arguments, "--annual-volatility", "nan"]) == 2


def test_analyze_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "bars.csv"
    simulate(path)
    assert main(["analyze", str(path), "--window", "24"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["coverage"]["bars"] == 300


def test_analyze_writes_output_and_database(tmp_path: Path) -> None:
    path, output, database = tmp_path / "b.csv", tmp_path / "r.json", tmp_path / "m.sqlite3"
    simulate(path)
    arguments = ["analyze", str(path), "--window", "24", "--output", str(output)]
    assert main([*arguments, "--database", str(database), "--symbol", "SYNTH"]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["parameters"]["window_bars"] == 24
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT symbol FROM instruments").fetchone() == ("SYNTH",)


def test_analyze_reports_invalid_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("not,a,candle\n", encoding="ascii")
    assert main(["analyze", str(path)]) == 2
    assert "line 1" in capsys.readouterr().err


def test_resample_command(tmp_path: Path) -> None:
    path, output = tmp_path / "b.csv", tmp_path / "h1.csv"
    simulate(path, bars=8)
    assert main(["resample", str(path), "--minutes", "60", "--output", str(output)]) == 0
    assert len(output.read_text(encoding="ascii").splitlines()) == 2


def test_resample_preserves_input_price_precision(tmp_path: Path) -> None:
    path, output = tmp_path / "fx.csv", tmp_path / "h1.csv"
    path.write_text(
        "2026.01.05,00:00,1.23456,1.23499,1.23401,1.23477,10\n"
        "2026.01.05,00:15,1.23477,1.23512,1.23450,1.23488,11\n",
        encoding="ascii",
    )
    assert main(["resample", str(path), "--minutes", "60", "--output", str(output)]) == 0
    assert output.read_text(encoding="ascii") == (
        "2026.01.05,00:00,1.23456,1.23512,1.23401,1.23488,21\n"
    )


def test_resample_rejects_non_multiple_minutes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, output = tmp_path / "b.csv", tmp_path / "o.csv"
    simulate(path, bars=8)
    assert main(["resample", str(path), "--minutes", "20", "--output", str(output)]) == 2
    assert "whole multiple" in capsys.readouterr().err
    assert not output.exists()


def test_simulate_refuses_prices_lost_to_rounding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "low.csv"
    arguments = ["simulate", "--bars", "5", "--seed", "1", "--initial-price", "0.001"]
    assert main([*arguments, "--output", str(output)]) == 2
    assert "does not fit" in capsys.readouterr().err
    assert not output.exists()
    assert main([*arguments, "--price-decimals", "8", "--output", str(output)]) == 0
    assert main(["analyze", str(output), "--window", "2", "--output", str(tmp_path / "r")]) == 0


@pytest.mark.parametrize("decimals", ["-1", "11"])
def test_simulate_rejects_invalid_price_decimals(tmp_path: Path, decimals: str) -> None:
    arguments = ["simulate", "--bars", "1", "--seed", "1", "--output", str(tmp_path / "a")]
    with pytest.raises(SystemExit):
        main([*arguments, f"--price-decimals={decimals}"])


def test_database_requires_explicit_symbol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, database = tmp_path / "b.csv", tmp_path / "m.sqlite3"
    simulate(path)
    assert main(["analyze", str(path), "--window", "24", "--database", str(database)]) == 2
    assert "--symbol" in capsys.readouterr().err
    assert not database.exists()


def test_invalid_symbol_writes_no_report(tmp_path: Path) -> None:
    path, output, database = tmp_path / "b.csv", tmp_path / "r.json", tmp_path / "m.sqlite3"
    simulate(path)
    arguments = ["analyze", str(path), "--window", "24", "--output", str(output)]
    assert main([*arguments, "--database", str(database), "--symbol", "BAD SYMBOL"]) == 2
    assert not output.exists()


def test_csv_example_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "eggs.csv"
    output.write_text("keep", encoding="utf-8")
    assert main(["csv-example", "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep"


def test_csv_example_matches_original_output(tmp_path: Path) -> None:
    output = tmp_path / "eggs.csv"
    assert main(["csv-example", "--output", str(output)]) == 0
    expected = ROOT / "tests" / "fixtures" / "python_docs_eggs.csv"
    assert output.read_bytes() == expected.read_bytes()


@pytest.mark.parametrize("bars", ["0", "-1", "5000001"])
def test_rejects_invalid_bar_counts(tmp_path: Path, bars: str) -> None:
    with pytest.raises(SystemExit):
        main(["simulate", "--bars", bars, "--seed", "1", "--output", str(tmp_path / "a.csv")])
