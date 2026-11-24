# m15 1.0.0 Release Notes

This is the first versioned release. It turns a 2018 CSV exercise into a tested toolkit for analyzing 15-minute OHLCV bars.

## Highlights

- Strict validation of MetaTrader-style exports.
- Volatility estimation that excludes returns spanning market gaps.
- Seeded simulation and reproducible JSON reports.
- Property-based and statistical tests.
- No third-party runtime dependencies.

## Upgrading

The `m15.py` script no longer exists. To reproduce its output, run:

```bash
uv run m15 csv-example --output eggs.csv
```

## Known limitations

- Timestamps are naive broker time.
- Resampling produces a bar for partially filled buckets.
- Range-based volatility estimators read low on discretely sampled data.
- Simulated data is not a realistic market model.
- The package is marked as not for upload to PyPI, and the repository declares no license.

Test results are in [reports/tests/summary.md](reports/tests/summary.md).
