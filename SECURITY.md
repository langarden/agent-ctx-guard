# Security

- Summaries are metadata-only by default; never put secrets into a custom
  `summary_fn` output.
- The archive contains raw messages — keep it on a machine you trust.
- `verify()` proves the ledger chain; `verify_archive()` proves the archive.
  Run both before trusting a restored session.

## Reporting

Report security issues privately; do not open public issues for them.