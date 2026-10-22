import tempfile
import unittest
from pathlib import Path

from intentprobe.store import Conflict, NotFound, Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / "sessions.sqlite3")

    def test_create_get_list_and_delete(self):
        saved = self.store.create("A local project", 3, "learned", {"time": "short"})
        self.assertEqual(saved, self.store.get(saved["id"]))
        self.assertEqual(self.store.list()[0]["id"], saved["id"])
        self.store.delete(saved["id"])
        with self.assertRaises(NotFound):
            self.store.get(saved["id"])

    def test_failed_mutation_rolls_back(self):
        saved = self.store.create("A local project", 3, "learned", {})

        def bad_change(record):
            record["answers"].append({"question_id": "hardware", "value": "cpu", "skipped": False})
            raise ValueError("Invalid change")

        with self.assertRaises(ValueError):
            self.store.mutate(saved["id"], saved["revision"], bad_change)
        self.assertEqual(self.store.get(saved["id"]), saved)

    def test_revision_is_checked_inside_transaction(self):
        saved = self.store.create("A local project", 3, "learned", {})
        changed = self.store.mutate(saved["id"], 0, lambda record: record.update(status="stopped"))
        self.assertEqual(changed["revision"], 1)
        with self.assertRaises(Conflict):
            self.store.mutate(saved["id"], 0, lambda record: record.update(status="active"))
        self.assertEqual(self.store.get(saved["id"])["status"], "stopped")
