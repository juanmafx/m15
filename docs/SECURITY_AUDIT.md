# Security Audit

Date: 2026-11-23. Scope: the working tree of branch `modernize/2026` and the three earlier commits. This is a self-review using the tools listed below, not an independent third-party assessment.

## Method

- Manual review of all source files.
- `ruff` with the `S` (Bandit-derived) rules.
- `mypy --strict`.
- `pip-audit` against the hash-locked development dependency set.
- Pattern search of the full git history for credentials, private keys, and contact details.

## Findings

| ID | Area | Severity | Status | Resolution |
| --- | --- | --- | --- | --- |
| A-01 | Legacy script wrote to a fixed relative path, truncating any existing file | Low | Fixed | Output path is explicit, and existing files are refused |
| A-02 | No validation of input data | Medium | Fixed | Strict field grammar, range checks, and file and line size limits |
| A-03 | Non-finite prices could corrupt results | Medium | Fixed | `nan`, `inf`, and exponent notation are rejected |
| A-04 | Partial output on interrupted writes | Low | Fixed | Temporary file, `fsync`, then atomic link or replace |
| A-05 | Output through a pre-existing symlink | Low | Fixed | The link itself is replaced and its target is not written |
| A-06 | SQL injection through the symbol label | Medium | Prevented | Parameterized statements and an allowlist for symbols |
| A-07 | Unpinned build and CI supply chain | Low | Fixed | Hash-locked `uv.lock`, actions pinned to commit SHAs, read-only token |
| A-08 | Market data file in git history | Informational | Open | See below |

## Open items

**A-08.** A 2018 market data export remains in the history of this repository, although it is not in the tree. It holds price bars only and no personal data, but its source and redistribution terms are not recorded. Removing it would require a history rewrite, which is the owner's decision.

## Not applicable

The project has no web interface, authentication, sessions, or network service, so XSS, CSRF, and two-factor authentication do not apply. It uses no `eval`, `exec`, `pickle`, shell execution, or password hashing. SHA-256 is used only as a content fingerprint.

## Residual risks

- A very large valid file can still consume memory up to the 256 MiB input limit and its parsed form.
- SHA-256 identifies input content but does not authenticate its origin.
