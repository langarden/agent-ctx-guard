# Changelog

## v0.1.0 (2026-11-12)

- Initial public release.
- `CtxFolder.fold()` — archive raw message + append metadata-only summary to
  a tamper-evident hash-chain ledger.
- `CtxFolder.unfold()` — reversible restore from verified archive.
- `verify()` / `verify_archive()` — full integrity proofs.
- Privacy by default: summaries never include raw content (customizable).
- Zero dependencies. 12 unit tests (`Ran 12 tests OK`).