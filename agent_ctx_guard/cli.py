# -*- coding: utf-8 -*-
"""agent-ctx-guard — verifiable context compression CLI (zero-dep).

Fold messages into a hash-checked archive + metadata-only ledger, unfold an
exact original, verify integrity.

Usage:
    agent-ctx-guard fold --message '<json>' [--prefix ./session]
    agent-ctx-guard fold --file transcript.jsonl [--prefix ./session]
    agent-ctx-guard unfold --message-id <id> [--prefix ./session]
    agent-ctx-guard verify [--prefix ./session]
    agent-ctx-guard status [--prefix ./session]

Exit codes: 0 = ok, 2 = verify fail / not found, 3 = error.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from .core import CtxFolder


def _folder(prefix: str) -> CtxFolder:
    return CtxFolder(path_prefix=prefix)


def cmd_fold(args: argparse.Namespace) -> int:
    messages: list = []
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": "bad transcript file: %s" % exc}, ensure_ascii=False))
            return 3
    else:
        try:
            messages.append(json.loads(args.message or "{}"))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": "bad message json: %s" % exc}, ensure_ascii=False))
            return 3

    try:
        folder = _folder(args.prefix)
        out = []
        for msg in messages:
            entry = folder.fold(msg)
            out.append({
                "message_id": entry["message_id"],   # full id, needed for unfold
                "summary": entry["summary"],
                "payload_hash": entry["payload_hash"][:16],
                "prev_hash": entry["prev_hash"][:16],
            })
        print(json.dumps({"folded": len(out), "entries": out,
                          "ledger": folder.ledger_path,
                          "archive": folder.archive_path},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": "fold failed: %s" % exc}, ensure_ascii=False))
        return 3


def cmd_unfold(args: argparse.Namespace) -> int:
    try:
        folder = _folder(args.prefix)
        msg = folder.unfold(args.message_id)
        if msg is None:
            print(json.dumps({"error": "message_id not found", "id": args.message_id},
                             ensure_ascii=False))
            return 2
        print(json.dumps({"message_id": args.message_id, "message": msg},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - archive tampered
        print(json.dumps({"error": "unfold failed (archive may be tampered): %s" % exc},
                         ensure_ascii=False))
        return 2


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        folder = _folder(args.prefix)
        ok_ledger = folder.verify()
        ok_archive = folder.verify_archive()
        print(json.dumps({"ok": ok_ledger and ok_archive,
                          "ledger": ok_ledger, "archive": ok_archive,
                          "entries": len(folder.entries),
                          "prefix": args.prefix or "(in-memory)"},
                         ensure_ascii=False, sort_keys=True))
        return 0 if (ok_ledger and ok_archive) else 2
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": "verify failed: %s" % exc}, ensure_ascii=False))
        return 3


def cmd_status(args: argparse.Namespace) -> int:
    try:
        folder = _folder(args.prefix)
        print(json.dumps({"ok": True, "engine": "agent_ctx_guard",
                          "entries": len(folder.entries),
                          "ledger": folder.ledger_path,
                          "archive": folder.archive_path},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": "%s" % exc}, ensure_ascii=False))
        return 3


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-ctx-guard",
                                     description="Verifiable context compression (fold/unfold/verify).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fold = sub.add_parser("fold", help="fold a message / transcript into ledger+archive")
    p_fold.add_argument("--message", default=None, help="a single message as JSON")
    p_fold.add_argument("--file", default=None, help="a JSONL transcript")
    p_fold.add_argument("--prefix", default="", help="file prefix (default: in-memory)")
    p_fold.set_defaults(fn=cmd_fold)

    p_unfold = sub.add_parser("unfold", help="restore an exact original message")
    p_unfold.add_argument("--message-id", required=True)
    p_unfold.add_argument("--prefix", default="", help="file prefix (default: in-memory)")
    p_unfold.set_defaults(fn=cmd_unfold)

    p_verify = sub.add_parser("verify", help="verify ledger + archive integrity")
    p_verify.add_argument("--prefix", default="", help="file prefix (default: in-memory)")
    p_verify.set_defaults(fn=cmd_verify)

    p_status = sub.add_parser("status", help="self-check install")
    p_status.add_argument("--prefix", default="")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args(argv)
    try:
        return int(args.fn(args))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": "unexpected: %s" % exc}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    sys.exit(main())
