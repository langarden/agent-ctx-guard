# -*- coding: utf-8 -*-
"""Demo/CLI entry: python -m agent_ctx_guard  |  agent-ctx-guard"""

import json
import sys

from .core import CtxFolder


def demo() -> None:
    folder = CtxFolder(path_prefix="")
    transcript = [
        {"role": "user", "content": "Fix the login bug and update tests."},
        {"role": "assistant",
         "content": "I see the token refresh cache is stale after expiry. "
                    "I'll patch auth.py and add unit tests for the refresh path."},
        {"role": "user", "content": "Also add a rate limiter, keep v1 compatible."},
    ]
    ids = []
    for msg in transcript:
        entry = folder.fold(msg)
        ids.append(entry["message_id"])
    print("=== ledger entries (metadata-only summaries) ===")
    for e in folder.entries:
        print(json.dumps({"message_id": e["message_id"][:8],
                          "summary": e["summary"],
                          "payload_hash": e["payload_hash"][:12]}, ensure_ascii=False))
    print("ledger verify:", folder.verify())
    print("archive verify:", folder.verify_archive())
    print("=== unfold restored message 2 ===")
    restored = folder.unfold(ids[1])
    print(restored["content"][:80])


def main() -> int:
    """Console entry point for the `agent-ctx-guard` script (demo mode)."""
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())