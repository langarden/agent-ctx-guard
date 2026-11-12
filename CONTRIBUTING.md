# Contributing

- Keep the library zero-dependency (Python 3.9+ stdlib).
- New features ship with unit tests; integrity paths must have tamper tests.
- Never persist raw payloads into the ledger — only into the archive with a payload_hash.
- Summaries must remain metadata-only by default.

```bash
pip install -e .
python -m unittest discover -s tests -v
```