# Security Audit

Date: 2026-11-24. Scope: the working tree of branch `modernize/2026` and the commits before it. This is an automated, agent-performed review using the tools listed below, not an independent third-party assessment.

## Method

- Manual review of all source files.
- `ruff` with the `S` (Bandit-derived) rules.
- `mypy --strict`.
- `pip-audit` against the hash-locked development dependency set.
- `gitleaks` with redaction over the full git history and the working tree.
- Pattern search of file contents across the git history for credentials, private keys, and contact details.
- Direct probing of the command-line interface with boundary inputs.

## Findings

| ID | Area | Severity | Status | Resolution |
| --- | --- | --- | --- | --- |
| A-01 | Legacy script wrote to a fixed relative path, truncating any existing file | Low | Fixed | Output path is explicit, and existing files are refused |
| A-02 | No validation of input data | Medium | Fixed | Strict field grammar, range checks, and file and line size limits |
| A-03 | Non-finite prices could corrupt results | Medium | Fixed | `nan`, `inf`, and exponent notation are rejected |
| A-04 | Partial output on interrupted writes | Low | Fixed | All file output uses a temporary file, `fsync`, then atomic link or replace |
| A-05 | Output through a pre-existing symlink | Low | Fixed | Refused by default; with `--force` the link is replaced and its target is not written. The `--database` path is excluded and follows symlinks |
| A-06 | SQL injection through the symbol label | Medium | Prevented | Parameterized statements and an allowlist for symbols |
| A-07 | Unpinned build and CI supply chain | Low | Fixed | Hash-locked `uv.lock` for dependencies, actions pinned to commit SHAs, read-only token. The `hatchling` build backend is pinned by version only |
| A-08 | Market data file in git history | Informational | Open | See below |
| A-09 | Rewritten files silently lost data: prices rounded to 2 decimals, and low prices became zero | High (integrity) | Fixed | Resampling keeps input precision, and unrepresentable values are errors |
| A-10 | Resampling accepted targets that split source bars across buckets | Medium (integrity) | Fixed | Target must be a whole multiple and bars must sit on the source grid |
| A-11 | Runs stored without `--symbol` were labeled `BTCUSD`, including synthetic data | Medium (integrity) | Fixed | `--symbol` is required with `--database` and validated before any output |
| A-12 | Rolling deviation kept residual error after an outlier left the window | Medium (integrity) | Fixed | Windows are merged from block prefixes and suffixes |
| A-13 | A tampered SQLite file could call schema functions | Low | Hardened | Connections set `PRAGMA trusted_schema = OFF` |

## Open items

**A-08.** A 2018 market data export remains in the history of this repository, although it is not in the tree. It holds price bars only and no personal data, but its source and redistribution terms are not recorded. Removing it would require a history rewrite, which is the owner's decision.

## Not applicable

The project has no web interface, authentication, sessions, or network service, so XSS, CSRF, and two-factor authentication do not apply. The runtime package uses no `eval`, `exec`, `pickle`, subprocess, or password hashing. The development-only report tool runs `git` with a fixed argument list and no shell. SHA-256 is used only as a content fingerprint.

## Residual risks

- A very large valid file can still consume memory up to the 256 MiB input limit and its parsed form.
- SHA-256 identifies input content but does not authenticate its origin.
- Opening a SQLite file from an untrusted source remains unsafe to rely on; `trusted_schema` reduces but does not remove that risk.
