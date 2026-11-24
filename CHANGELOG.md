# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## [1.0.0]

### Added

- Installable `m15` package and command-line interface.
- Strict parser for MetaTrader-style M15 CSV files with input hashing.
- Gap detection, gap-aware returns, four volatility estimators, maximum drawdown, rolling statistics, and precision-preserving resampling to whole multiples of the source timeframe.
- Seeded geometric Brownian motion simulator.
- Optional SQLite schema and persistence.
- Unit, property-based, and statistical test suites with a committed test report.
- CI with least-privilege permissions, pinned actions, and a locked dependency set.
- Architecture, security, and release documentation.

### Changed

- **Breaking:** the top-level `m15.py` script is replaced by the `m15` package and CLI.
- The original exercise now runs on Python 3 and lives in `src/m15/legacy/`, with credit to the Python documentation.
- `eggs.csv` moved to `tests/fixtures/python_docs_eggs.csv`.

### Security

- The exercise no longer writes over a fixed file name in the working directory.
- File output is atomic and refuses to overwrite without `--force`.
- SQLite connections disable `trusted_schema`, limiting what functions a tampered database schema can call.
