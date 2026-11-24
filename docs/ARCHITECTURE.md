# Architecture

## Design goals

1. **Correct under real data.** Gaps, malformed rows, and unordered bars are handled explicitly.
2. **Reproducible.** A report records the input SHA-256 and parameters, and simulation is fully determined by its seed.
3. **Small trusted surface.** The runtime uses only the Python standard library.

## Module structure

```text
src/m15/
  cli.py                     argument parsing and exit codes
  errors.py                  typed error hierarchy
  domain/candle.py           immutable, self-validating bar
  data/
    metatrader_csv.py        strict parsing, hashing, and formatting
    synthetic.py             seeded geometric Brownian motion
  analytics/
    returns.py               log returns, gap-aware
    rolling.py               sliding moments and extrema
    volatility.py            four volatility estimators
    drawdown.py              maximum drawdown
    gaps.py                  missing-bar detection
    resample.py              timeframe aggregation
    report.py                composes the JSON report
  storage/
    files.py                 atomic file output
    schema.sql               packaged copy of db/schema.sql
    sqlite_repository.py     parameterized persistence
  legacy/python_docs_csv.py  the credited 2018 exercise
```

Dependencies point one way: `cli` to `analytics`, `data`, and `storage`, and all of those to `domain`. The domain layer imports nothing but the error types. This project has no client and server split, so there is no `frontend/` or `backend/`.

## Data flow

```text
CSV file -> read_series (validate + SHA-256) -> Candle tuple -> build_report -> JSON
                                                     |                           |
                                                     +-> resample -> CSV         +-> optional SQLite
```

## Algorithms and complexity

For `n` bars and window `w`:

| Operation | Method | Time | Extra space |
| --- | --- | --- | --- |
| Parse and validate | Single pass | O(n) | O(n) |
| Log returns, gaps | Adjacent pairs | O(n) | O(n) |
| Rolling mean and deviation | Sliding Welford update | O(n) | O(n) output |
| Rolling min and max | Monotonic deque | O(n) amortized | O(w) plus output |
| Maximum drawdown | Running peak | O(n) | O(1) |
| Volatility estimators | Compensated summation (`math.fsum`) | O(n) | O(n) inside `fsum` |
| Resampling | Group by aligned bucket | O(n) | O(n) |
| Simulation | `substeps` per bar | O(n * substeps) | O(n) |

### Rolling moments

The window update replaces the leaving value `y` with the entering value `x`:

```text
mean' = mean + (x - y) / w
S'    = S + (x - y) * (x - mean' + y - mean)
```

Sliding updates can accumulate floating-point drift over very long series. Property tests compare them with direct computation on series of up to 80 values.

### Volatility estimators

Per-bar variance, averaged over bars, with `H`, `L`, `O`, `C` the bar prices:

```text
Parkinson        ln(H/L)^2 / (4 ln 2)
Garman-Klass     0.5 ln(H/L)^2 - (2 ln 2 - 1) ln(C/O)^2
Rogers-Satchell  ln(H/C) ln(H/O) + ln(L/C) ln(L/O)
```

Close-to-close volatility is the sample standard deviation of contiguous log returns. Returns that span a gap are excluded because they cover an unknown number of bars.

**Known bias.** Range estimators assume continuous monitoring. On discretely sampled paths the observed high and low understate the true extremes, so these estimators read low. The test suite demonstrates this: bias is negative and shrinks as `substeps` grows. Real bars are also affected by microstructure noise, which this project does not model.

### Simulation

Log price follows exact geometric Brownian motion increments:

```text
ln S(t + dt) = ln S(t) + (mu - sigma^2 / 2) dt + sigma sqrt(dt) Z
```

Normals are produced by inverse-CDF sampling from `random.Random.random()`, whose sequence Python keeps stable for a given seed. Volume is an independent lognormal draw and is purely illustrative. Simulated data is not a model of real markets, since it has no volatility clustering or fat tails.

### Resampling

Buckets are aligned to the Unix epoch in the file's naive clock. For nested widths, resampling composes: `resample(resample(x, 60), 240) == resample(x, 240)`. Property tests verify this, along with conservation of volume and extremes. Empty buckets produce no bar.

## Persistence

`db/schema.sql` is the public schema, and a test keeps it identical to the packaged copy. Candles use a composite primary key, so re-importing a file is idempotent. Each analysis appends one immutable row to `analysis_runs`.

## Recommended evolution

- For very large histories, move to columnar storage and vectorized computation.
- Add timezone normalization if the broker's server offset becomes known.
- Add a jump-robust estimator such as bipower variation for real intraday data.

## References

- Parkinson, M. (1980). The Extreme Value Method for Estimating the Variance of the Rate of Return. *Journal of Business*, 53(1).
- Garman, M. B., and Klass, M. J. (1980). On the Estimation of Security Price Volatilities from Historical Data. *Journal of Business*, 53(1).
- Rogers, L. C. G., and Satchell, S. E. (1991). Estimating Variance from High, Low and Closing Prices. *Annals of Applied Probability*, 1(4).
- Welford, B. P. (1962). Note on a Method for Calculating Corrected Sums of Squares and Products. *Technometrics*, 4(3).
