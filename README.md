# agent-ctx-guard

> **压缩是过程，可验证才是结果。**  
> Verifiable context compression for agent sessions — fold, reversible unfold, tamper-evident ledger.

`agent-ctx-guard` folds a long session transcript into small metadata summaries while preserving **every original message** in a hash-checked archive. The ledger is a tamper-evident JSONL hash chain; the archive is byte-verifiable; summaries are metadata-only, so you can publish what was compressed **without leaking raw content**. Part of the **Verifiable-agent family**.

## Why

Context compression is the hot topic in the agent world. But most compressors are black boxes — you never know **what** was dropped. This library answers that: compression is a *process*, and `agent-ctx-guard` makes it a *verifiable result*. It is the memory-ledger approach applied to session compression: **fold → reversible unfold → prove nothing was lost**.

**What you get:**

- **`fold()`** — archive the raw message, append a metadata-only summary to a tamper-evident ledger.
- **`unfold()`** — restore the exact raw message from the archive, verified by sha256 (detects archive tampering).
- **`verify()`** / **`verify_archive()`** — prove both the ledger chain and the archive are untampered.
- **Privacy by default** — summaries never include raw content (customizable); raw payloads live only in the hash-checked archive.
- Zero dependencies, pure Python 3.9+ stdlib.

## Install

```bash
pip install agent-ctx-guard
```

## Quick start

```python
from agent_ctx_guard import CtxFolder

folder = CtxFolder(path_prefix="./my_session")   # writes .ctxg.ledger.jsonl + .ctxg.archive.jsonl

# Fold every message as it scrolls out of your active window
for msg in transcript:
    entry = folder.fold(msg)          # entry["summary"] has the metadata

# Later, restore an exact original
restored = folder.unfold(entry["message_id"])
print(restored["content"])

# Prove integrity any time
assert folder.verify() is True        # ledger chain untampered
assert folder.verify_archive() is True
```

## Proof of life

```
$ python -m agent_ctx_guard
=== ledger entries (metadata-only summaries) ===
{'message_id': '8a845d8f', 'summary': {'role': 'user', 'content_length': 35, 'content_sha256': '482635470c5f087c', 'tokens': 0, 'type': ''}, 'payload_hash': 'f0b074c31dbf'}
{'message_id': '5f72f10e', 'summary': {'role': 'assistant', 'content_length': 112, 'content_sha256': 'c84699ba2cd454cf', 'tokens': 0, 'type': ''}, 'payload_hash': '75543233a758'}
ledger verify: True
archive verify: True
=== unfold restored message 2 ===
I see the token refresh cache is stale after expiry. I'll patch auth.py and add unit tests for the refresh path.
```

Notice: the ledger contains **no raw bodies at all** — only role / length / digest. The proof lives in the hash chain, the content stays in the verified archive, and `unfold()` restores the exact original byte-for-byte.

## Invariants

| # | Invariant | Enforced by |
|:--|:--|:--|
| 1 | Ledger is a sha256 hash chain | `fold()` + `verify()` |
| 2 | Archive payload hash must match on unfold | `unfold()` |
| 3 | Summaries never carry raw secrets by default | `default_summary` |
| 4 | Reload from disk preserves chain + archive | `CtxFolder.__init__` |
| 5 | Empty folder verifies True (genesis) | `verify()` |

## Roadmap ideas

- CLI (`ctx-guard fold --file ... --ranges ...`).
- Integration hook for LLM-generated digests via custom `summary_fn`.
- Batch compression with prefix-cache-aware range selection.

## License

MIT. [中文版](docs/README.zh-CN.md)