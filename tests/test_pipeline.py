import json
import tempfile
import unittest
from pathlib import Path

from jumping_spyder.classifiers import RuleClassifier
from jumping_spyder.domain import Classification, Post
from jumping_spyder.pipeline import process_pending
from jumping_spyder.sinks import PreviewSink
from jumping_spyder.store import Store


def post(id="1", text="I am bullish on SOL.", source="fixture"):
    return Post(source, id, "example", text, "https://example.com/" + id, "2026-01-01T00:00:00Z")


class CountingClassifier(RuleClassifier):
    def __init__(self):
        self.calls = 0

    def classify(self, post):
        self.calls += 1
        return super().classify(post)


class Sink:
    destination = "test-delivery"

    def __init__(self, fail=False):
        self.fail, self.messages = fail, []

    def send(self, post, result):
        if self.fail:
            raise RuntimeError("secret-provider-token-must-never-be-persisted")
        self.messages.append(post.key)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "inbox.sqlite3"
        self.store = Store(self.path)
        self.classifier = CountingClassifier()
        self.sink = Sink()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_all_unseen_posts_are_processed_oldest_first(self):
        self.store.ingest([post("2"), post("1")])
        stats = process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(stats.delivered, 2)
        self.assertEqual(self.sink.messages, ["fixture:1", "fixture:2"])

    def test_duplicate_ingestion_and_rerun_do_not_redeliver(self):
        self.assertEqual(self.store.ingest([post(), post()]), 1)
        process_pending(self.store, self.classifier, self.sink)
        self.store.ingest([post()])
        process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(self.classifier.calls, 1)
        self.assertEqual(len(self.sink.messages), 1)

    def test_source_namespaces_do_not_collide(self):
        self.assertEqual(self.store.ingest([post(source="x"), post(source="youtube")]), 2)

    def test_failed_delivery_survives_restart_without_reclassification(self):
        self.store.ingest([post()])
        self.sink.fail = True
        stats = process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(stats.failed, 1)
        self.store.close()
        self.store = Store(self.path)
        row = self.store.records(self.sink.destination)[0]
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["delivery_attempts"], 1)
        self.assertNotIn("secret", json.dumps(row))
        self.sink.fail = False
        process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(self.classifier.calls, 1)
        self.assertEqual(self.store.records(self.sink.destination)[0]["state"], "delivered")

    def test_failed_classification_does_not_block_other_posts(self):
        class SometimesBroken(CountingClassifier):
            def classify(self, item):
                if item.id == "1":
                    raise ValueError("invalid response")
                return super().classify(item)

        self.store.ingest([post("1"), post("2")])
        stats = process_pending(self.store, SometimesBroken(), self.sink)
        self.assertEqual((stats.failed, stats.delivered), (1, 1))
        process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(set(self.sink.messages), {"fixture:1", "fixture:2"})

    def test_flagged_and_neutral_content_is_suppressed(self):
        self.store.ingest(
            [post("1", "Weekly release notes."), post("2", "Bullish! Guaranteed profit.")]
        )
        stats = process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(stats.suppressed, 2)
        self.assertEqual(self.sink.messages, [])

    def test_unknown_risk_never_alerts(self):
        class Unknown(RuleClassifier):
            def classify(self, item):
                return Classification("BULLISH", "UNKNOWN", "Ambiguous origin.", item.text)

        self.store.ingest([post()])
        self.assertEqual(process_pending(self.store, Unknown(), self.sink).suppressed, 1)

    def test_preview_does_not_consume_telegram_destination(self):
        self.store.ingest([post()])
        process_pending(self.store, self.classifier, PreviewSink())
        process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(len(self.sink.messages), 1)
        self.assertEqual(self.classifier.calls, 1)

    def test_changed_source_content_rolls_back_batch(self):
        self.store.ingest([post()])
        with self.assertRaises(ValueError):
            self.store.ingest([post("2"), post("1", "Changed source text")])
        self.assertEqual(len(self.store.records("test")), 1)

    def test_worker_lock_rejects_concurrent_process(self):
        other = Store(self.path)
        try:
            with self.store.lock():
                with self.assertRaises(RuntimeError):
                    with other.lock():
                        pass
        finally:
            other.close()

    def test_invalid_adapter_result_is_not_saved(self):
        class Broken(RuleClassifier):
            def classify(self, item):
                return Classification("BUY", "CLEAR", "invalid", "not in the source")

        self.store.ingest([post()])
        self.assertEqual(process_pending(self.store, Broken(), self.sink).failed, 1)
        self.assertIsNone(self.store.records("test")[0]["result"])

    def test_limit_leaves_backlog_for_next_run(self):
        self.store.ingest([post("1"), post("2")])
        self.assertEqual(process_pending(self.store, self.classifier, self.sink, 1).delivered, 1)
        self.assertEqual(len(self.store.pending(self.sink.destination)), 1)

    def test_source_times_are_normalized_before_processing_order(self):
        late = Post(
            "fixture",
            "a",
            "example",
            "Bullish",
            "https://example.com/a",
            "2026-01-01T00:00:00-05:00",
        )
        early = Post(
            "fixture", "z", "example", "Bullish", "https://example.com/z", "2026-01-01T02:00:00Z"
        )
        self.store.ingest([late, early])
        process_pending(self.store, self.classifier, self.sink)
        self.assertEqual(self.sink.messages, ["fixture:z", "fixture:a"])

    def test_future_schema_is_rejected(self):
        self.store.conn.execute("PRAGMA user_version=99")
        with self.assertRaises(RuntimeError):
            Store(self.path)

    def test_poison_item_cannot_starve_new_items_with_bounded_runs(self):
        class Broken(RuleClassifier):
            def classify(self, item):
                raise ValueError("bad output")

        self.store.ingest([post("1"), post("2")])
        process_pending(self.store, Broken(), self.sink, 1)
        process_pending(self.store, self.classifier, self.sink, 1)
        self.assertEqual(self.sink.messages, ["fixture:2"])

    def test_database_file_symlink_shares_the_worker_lock(self):
        alias = Path(self.temp.name) / "alias.sqlite3"
        alias.symlink_to(self.path)
        other = Store(alias)
        try:
            self.assertEqual(self.store.path, other.path)
            with self.store.lock():
                with self.assertRaises(RuntimeError):
                    with other.lock():
                        self.fail("Symlink alias bypassed the active database lock")
        finally:
            other.close()
