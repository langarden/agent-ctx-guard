# -*- coding: utf-8 -*-
"""agent-ctx-guard — verifiable context compression.

Compression is a process; verifiability is the result.

This library folds a long session transcript into small, self-describing
summary entries while preserving every original message in a hash-checked
archive. The ledger is tamper-evident (JSONL + sha256 chain); the archive is
byte-verifiable; and the summaries are deliberately metadata-only, so the
ledger can be published without leaking raw content.

Design intent (borrowed from the group's memory-ledger philosophy, NOT code
from billion-context):

  * fold   -> consume a message, emit a metadata summary, archive the raw
  * unfold -> restore the raw message from the archive, verified by hash
  * verify -> prove the whole ledger chain is untampered
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64

SummaryFn = Callable[[Dict[str, Any]], Dict[str, Any]]


def default_summary(message: Dict[str, Any], max_chars: int = 200) -> Dict[str, Any]:
    """Build a pure-metadata summary. NEVER includes raw content.

    The default keeps the ledger publishable without leaking any body text:
    role / type / content length / a content digest (sha256 prefix). Provide a
    custom ``summary_fn`` to CtxFolder.fold() if you want an LLM digest —
    the summary function output is yours to control, keep secrets out of it.
    """
    content = message.get("content", "")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return {
        "role": str(message.get("role", "?")),
        "content_length": len(content),
        "content_sha256": _sha256(content.encode("utf-8"))[:16],
        "tokens": message.get("tokens") or 0,
        "type": str(message.get("type", "")),
    }


def _canonical(record: Dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CtxFolder:
    """Folds transcripts into a verifiable ledger + reversible archive."""

    def __init__(self, path_prefix: str = "") -> None:
        self.path_prefix = path_prefix
        self.ledger_path = path_prefix + ".ctxg.ledger.jsonl"
        self.archive_path = path_prefix + ".ctxg.archive.jsonl"
        self._lock = threading.Lock()
        self._ledger: List[Dict[str, Any]] = []
        self._archive: Dict[str, Dict[str, Any]] = {}
        if self.ledger_path and os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self._ledger.append(json.loads(line))
        if self.archive_path and os.path.exists(self.archive_path):
            with open(self.archive_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self._archive[entry["message_id"]] = entry

    # ------------------------------------------------------------------ API
    @property
    def last_hash(self) -> str:
        return self._ledger[-1]["entry_hash"] if self._ledger else GENESIS_HASH

    @property
    def entries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._ledger)

    def fold(self, message: Dict[str, Any],
             summary_fn: Optional[SummaryFn] = None) -> Dict[str, Any]:
        """Archive a raw message and append a summary record to the ledger.

        Returns the ledger entry. The raw message is preserved in the archive
        keyed by ``message_id``; the ledger entry carries the archive id + a
        sha256 of the raw payload (never the raw payload itself).
        """
        if not isinstance(message, dict):
            raise ValueError("fold() expects a dict message")
        summary_fn = summary_fn or default_summary
        message_id = uuid.uuid4().hex
        payload_hash = _sha256(_canonical(message))
        summary = summary_fn(message)
        with self._lock:
            # preserve archive first (durable), then ledger entry referencing it
            archive_entry = {
                "message_id": message_id,
                "payload_hash": payload_hash,
                "message": message,
            }
            self._archive[message_id] = archive_entry
            self._save_archive(archive_entry)
            entry = {
                "ts": time.time(),
                "message_id": message_id,
                "summary": summary,
                "payload_hash": payload_hash,      # proves archive integrity
                "prev_hash": self.last_hash,
            }
            entry["entry_hash"] = _sha256(_canonical(entry))
            self._ledger.append(entry)
            self._save_ledger(entry)
            return dict(entry)

    def unfold(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Restore a raw message from the archive, verified against its hash."""
        with self._lock:
            entry = self._archive.get(message_id)
            if entry is None:
                return None
            payload_hash = _sha256(_canonical(entry["message"]))
            if payload_hash != entry["payload_hash"]:
                raise ValueError("archive tampered: message_id %s hash mismatch" % message_id)
            return dict(entry["message"])

    def verify(self) -> bool:
        """Proof that the ledger chain is untampered (hashes + prev links)."""
        prev = GENESIS_HASH
        for entry in self._ledger:
            body = {k: v for k, v in entry.items() if k != "entry_hash"}
            if body.get("prev_hash") != prev:
                return False
            if _sha256(_canonical(body)) != entry.get("entry_hash"):
                return False
            prev = entry["entry_hash"]
        return True

    def verify_archive(self) -> bool:
        """Every archive entry's payload hash must match its stored hash."""
        with self._lock:
            for message_id, entry in self._archive.items():
                if _sha256(_canonical(entry["message"])) != entry["payload_hash"]:
                    return False
        return True

    # -------------------------------------------------------------- storage
    def _save_ledger(self, entry: Dict[str, Any]) -> None:
        if not self.ledger_path:
            return
        directory = os.path.dirname(os.path.abspath(self.ledger_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def _save_archive(self, entry: Dict[str, Any]) -> None:
        if not self.archive_path:
            return
        directory = os.path.dirname(os.path.abspath(self.archive_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.archive_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")