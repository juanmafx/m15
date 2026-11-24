# Architecture

## Design goals

1. **Correct under real data.** Gaps, malformed rows, and unordered bars are handled explicitly.
2. **Reproducible.** A report records the input SHA-256 and parameters, and simulation is fully determined by its seed and parameters.
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

Dependencies point one way: `cli` to `analytics`, `data`, and `storage`, and all of those to `domain`. `legacy` uses `storage` for atomic output. The domain layer imports nothing but the error types. This project has no client and server split, so there is no `frontend/` or `backend/`.

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
| Rolling mean and deviation | Block prefix and suffix merge | O(n) | O(n) |
| Rolling min and max | Monotonic deque | O(n) amortized | O(w) plus output |
| Maximum drawdown | Running peak | O(n) | O(1) |
| Volatility estimators | Compensated summation (`math.fsum`) | O(n) | O(n) inside `fsum` |
| Resampling | Group by aligned bucket | O(n) | O(n) |
| Simulation | `substeps` per bar | O(n * substeps) | O(n) |

### Rolling moments

The series is cut into blocks of `w` values. Each window is the merge of one block suffix and one block prefix, using the pairwise update for two partial results:

```text
n     = n1 + n2
d     = mean2 - mean1
mean  = mean1 + d * n2 / n
S     = S1 + S2 + d^2 * n1 * n2 / n
```

Values are never subtracted out of a running total, so an outlier leaves no residual error once it exits the window. A regression test covers this case, and property tests compare results with direct computation on series of up to 80 values.

### Volatility estimators

Per-bar variance, averaged over bars, with `H`, `L`, `O`, `C` the bar prices:

```text
Parkinson        ln(H/L)^2 / (4 ln 2)
Garman-Klass     0.5 ln(H/L)^2 - (2 ln 2 - 1) ln(C/O)^2
Rogers-Satchell  ln(H/C) ln(H/O) + ln(L/C) ln(L/O)
```

Close-to-close volatility is the sample standard deviation of contiguous log returns. Returns that span a gap are excluded because they cover an unknown number of bars. Intervals that are not a whole multiple of the bar spacing are also excluded and are counted in the report as `irregular_intervals`.

**Known bias.** Range estimators assume continuous monitoring. On discretely sampled paths the observed high and low understate the true extremes, so these estimators read low. The test suite demonstrates this: bias is negative and shrinks as `substeps` grows. Real bars are also affected by microstructure noise, which this project does not model.

### Simulation

Log price follows exact geometric Brownian motion increments:

```text
ln S(t + dt) = ln S(t) + (mu - sigma^2 / 2) dt + sigma sqrt(dt) Z
```

Normals are produced by inverse-CDF sampling from `random.Random.random()`, whose sequence Python keeps stable for a given seed. Volume is an independent lognormal draw and is purely illustrative. Simulated data is not a model of real markets, since it has no volatility clustering or fat tails.

### Resampling

Buckets are aligned to the Unix epoch in the file's naive clock. For nested widths, resampling composes: `resample(resample(x, 60), 240) == resample(x, 240)`. Property tests verify this, along with conservation of volume and extremes. Empty buckets produce no bar, and a partially filled bucket still produces one. The target must be a whole multiple of the source timeframe and bars must sit on the source grid, because a bar cannot be split across two buckets. Output keeps the widest price precision found in the input.

## Persistence

`db/schema.sql` is the public schema, and a test keeps it identical to the packaged copy. Candles use a composite primary key, so re-importing a file is idempotent. Importing changed values for an existing bar replaces the stored bar, while earlier runs keep their own report JSON. Each analysis appends one immutable row to `analysis_runs`.

## Recommended evolution

- For very large histories, move to columnar storage and vectorized computation.
- Add timezone normalization if the broker's server offset becomes known.
- Add a jump-robust estimator such as bipower variation for real intraday data.

## References

- Parkinson, M. (1980). The Extreme Value Method for Estimating the Variance of the Rate of Return. *Journal of Business*, 53(1).
- Garman, M. B., and Klass, M. J. (1980). On the Estimation of Security Price Volatilities from Historical Data. *Journal of Business*, 53(1).
- Rogers, L. C. G., and Satchell, S. E. (1991). Estimating Variance from High, Low and Closing Prices. *Annals of Applied Probability*, 1(4).
- Chan, T. F., Golub, G. H., and LeVeque, R. J. (1983). Algorithms for Computing the Sample Variance: Analysis and Recommendations. *The American Statistician*, 37(3).
