# -*- coding: utf-8 -*-
"""agent-ctx-guard tests — fold/unfold/verify + tamper detection."""

import json
import os
import tempfile
import unittest

from agent_ctx_guard import CtxFolder, default_summary
from agent_ctx_guard.core import GENESIS_HASH, _canonical, _sha256


class FoldTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefix = os.path.join(self.tmp.name, "sess")
        self.folder = CtxFolder(path_prefix=self.prefix)

    def tearDown(self):
        self.tmp.cleanup()

    def _msg(self, role, content, tokens=0):
        return {"role": role, "content": content, "tokens": tokens}

    def test_fold_creates_entry(self):
        entry = self.folder.fold(self._msg("user", "hello world"))
        self.assertIn("entry_hash", entry)
        self.assertEqual(entry["summary"]["role"], "user")
        self.assertTrue(entry["payload_hash"])

    def test_summary_is_metadata_only(self):
        entry = self.folder.fold(self._msg("user", "SECRET_TOKEN_ABC123"))
        # raw secret must not appear in the ledger entry or its summary
        raw_ledger = json.dumps(entry, ensure_ascii=False)
        self.assertNotIn("SECRET_TOKEN_ABC123", raw_ledger)
        self.assertNotIn("abstract", entry["summary"])
        self.assertIn("content_sha256", entry["summary"])

    def test_summary_hash_len_type(self):
        entry = self.folder.fold(self._msg("assistant", "x" * 1000))
        self.assertEqual(entry["summary"]["content_length"], 1000)
        self.assertEqual(entry["summary"]["role"], "assistant")
        self.assertEqual(entry["summary"]["tokens"], 0)

    def test_unfold_restores_original(self):
        msg = self._msg("assistant", "original body", 42)
        entry = self.folder.fold(msg)
        restored = self.folder.unfold(entry["message_id"])
        self.assertEqual(restored["content"], "original body")
        self.assertEqual(restored["tokens"], 42)

    def test_unfold_unknown_returns_none(self):
        self.assertIsNone(self.folder.unfold("does-not-exist"))

    def test_custom_summary_fn(self):
        def fn(m):
            return {"role": m["role"], "digest": "MY-DIGEST"}
        entry = self.folder.fold(self._msg("user", "hi"), summary_fn=fn)
        self.assertEqual(entry["summary"]["digest"], "MY-DIGEST")


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefix = os.path.join(self.tmp.name, "sess")
        self.folder = CtxFolder(path_prefix=self.prefix)

    def tearDown(self):
        self.tmp.cleanup()

    def test_verify_empty_is_true(self):
        self.assertTrue(self.folder.verify())

    def test_verify_chain_after_folds(self):
        for i in range(5):
            self.folder.fold({"role": "user", "content": "msg %d" % i})
        self.assertTrue(self.folder.verify())

    def test_tamper_detected(self):
        for i in range(3):
            self.folder.fold({"role": "user", "content": "msg %d" % i})
        self.folder._ledger[1]["summary"]["abstract"] = "TAMPERED"  # noqa: SLF001
        self.assertFalse(self.folder.verify())

    def test_archive_verify(self):
        for i in range(3):
            self.folder.fold({"role": "user", "content": "msg %d" % i})
        self.assertTrue(self.folder.verify_archive())

    def test_archive_tamper_detected(self):
        entry = self.folder.fold({"role": "user", "content": "real content"})
        mid = entry["message_id"]
        self.folder._archive[mid]["message"]["content"] = "CHANGED"  # noqa: SLF001
        self.assertFalse(self.folder.verify_archive())

    def test_reload_from_disk_preserves_chain(self):
        for i in range(3):
            self.folder.fold({"role": "user", "content": "msg %d" % i})
        reloaded = CtxFolder(path_prefix=self.prefix)
        self.assertEqual(len(reloaded.entries), 3)
        self.assertTrue(reloaded.verify())
        self.assertTrue(reloaded.verify_archive())
        mid = reloaded.entries[1]["message_id"]
        self.assertEqual(reloaded.unfold(mid)["content"], "msg 1")


class DefaultSummaryTest(unittest.TestCase):
    def test_empty_content(self):
        s = default_summary({"role": "user"})
        self.assertEqual(s["role"], "user")
        self.assertEqual(s["content_length"], 0)

    def test_never_contains_raw_content(self):
        s = default_summary({"role": "user", "content": "secret-body-xyz"})
        blob = json.dumps(s, ensure_ascii=False)
        self.assertNotIn("secret-body-xyz", blob)
        self.assertIn("content_sha256", s)


if __name__ == "__main__":
    unittest.main()