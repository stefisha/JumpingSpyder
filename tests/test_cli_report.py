import contextlib
import io
import os
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from test_pipeline import post

from jumping_spyder.classifiers import RuleClassifier
from jumping_spyder.cli import load_env, main
from jumping_spyder.evaluation import evaluate
from jumping_spyder.pipeline import process_pending
from jumping_spyder.report import render_report
from jumping_spyder.sinks import PreviewSink
from jumping_spyder.store import Store


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_runs_offline_and_is_idempotent(self):
        with patch(
            "urllib.request.OpenerDirector.open", side_effect=AssertionError("Network forbidden")
        ):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                args = ["demo", "--output", str(self.root)]
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args), 0)
        text = output.getvalue()
        self.assertIn('"inserted": 8', text)
        self.assertIn('"inserted": 0', text)
        self.assertIn('"delivered": 0', text)
        self.assertTrue((self.root / "index.html").exists())
        html = (self.root / "index.html").read_text()
        self.assertIn("data:image/png;base64,", html)
        self.assertNotIn("@@LOGO@@", html)

    def test_report_escapes_source_content_and_template_markers(self):
        store = Store(self.root / "db")
        try:
            store.ingest([post(text='<script>alert("x")</script> @@MODE@@ bullish')])
            process_pending(store, RuleClassifier(), PreviewSink())
            target = render_report(store, "local-review", self.root / "report.html")
            html = target.read_text()
            self.assertNotIn('<script>alert("x")</script>', html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("@@MODE@@", html)
            self.assertIn("reviewed locally", html)
        finally:
            store.close()

    def test_evaluation_records_failures_instead_of_hiding_them(self):
        path = files("jumping_spyder").joinpath("data/evaluation.json")
        result = evaluate(path, RuleClassifier(), self.root / "metrics.json")
        self.assertEqual(result["samples"], 24)
        self.assertLess(result["accuracy"], 1)
        self.assertTrue(any(not case["correct"] for case in result["cases"]))
        self.assertEqual(len(result["dataset_sha256"]), 64)
        self.assertEqual(sum(sum(row.values()) for row in result["confusion_matrix"].values()), 24)

    def test_env_file_is_literal_and_preserves_existing_environment(self):
        env = self.root / ".env"
        env.write_text('OPENAI_MODEL="file-model"\nX_BEARER_TOKEN=$(echo never-executed)\n')
        with patch.dict(os.environ, {"OPENAI_MODEL": "shell-model"}, clear=True):
            load_env(env)
            self.assertEqual(os.environ["OPENAI_MODEL"], "shell-model")
            self.assertEqual(os.environ["X_BEARER_TOKEN"], "$(echo never-executed)")

    def test_missing_credentials_fail_before_ingesting(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            code = main(
                [
                    "ingest",
                    "--input",
                    "examples/posts.json",
                    "--classifier",
                    "openai",
                    "--database",
                    str(self.root / "db"),
                ]
            )
        self.assertEqual(code, 1)
        self.assertIn("OPENAI_API_KEY", output.getvalue())
        self.assertFalse((self.root / "db").exists())

    def test_preview_then_real_destination_has_separate_pending_records(self):
        # Integration boundary is mocked: this test must never send a real message.
        args = [
            "ingest",
            "--input",
            "examples/posts.json",
            "--database",
            str(self.root / "db"),
            "--report",
            str(self.root / "report.html"),
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
            with patch.dict(
                os.environ, {"TELEGRAM_BOT_TOKEN": "1:test", "TELEGRAM_CHAT_ID": "test"}
            ):
                with patch(
                    "jumping_spyder.http.JsonHTTP.request",
                    return_value={"ok": True, "result": {"message_id": 1}},
                ) as send:
                    self.assertEqual(
                        main(
                            [
                                "retry",
                                "--database",
                                str(self.root / "db"),
                                "--report",
                                str(self.root / "report.html"),
                                "--notify",
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(send.call_count, 2)

    def test_report_command_does_not_classify(self):
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch.object(RuleClassifier, "classify", side_effect=AssertionError),
        ):
            self.assertEqual(
                main(
                    [
                        "report",
                        "--database",
                        str(self.root / "db"),
                        "--report",
                        str(self.root / "empty.html"),
                    ]
                ),
                0,
            )
        self.assertIn("No content yet", (self.root / "empty.html").read_text())

    def test_fixture_rejects_non_https_source_url(self):
        from jumping_spyder.domain import Post

        data = post().to_dict()
        data["url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            Post(**data)

    def test_naive_source_timestamp_is_rejected(self):
        from jumping_spyder.domain import Post

        data = post().to_dict()
        data["published_at"] = "2026-01-01T00:00:00"
        with self.assertRaises(ValueError):
            Post(**data)

    def test_malformed_fixture_returns_clear_error_without_traceback(self):
        fixture = self.root / "bad.json"
        fixture.write_text('[{"unexpected": "value"}]')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = main(["ingest", "--input", str(fixture), "--database", str(self.root / "db")])
        self.assertEqual(code, 1)
        self.assertIn("six documented source fields", output.getvalue())

    def test_malformed_evaluation_cases_fail_cleanly_before_classification(self):
        import json

        valid = {"id": "valid", "text": "Bullish", "label": "BULLISH", "risk_flagged": False}
        malformed = [
            {},
            None,
            "not a case",
            {**valid, "id": []},
            {**valid, "id": 1},
            {**valid, "id": ""},
            {**valid, "text": False},
            {**valid, "label": "BUY"},
            {**valid, "risk_flagged": "false"},
            {**valid, "extra": True},
        ]
        documents = [
            {},
            None,
            "not a list",
            [],
            [valid, valid],
            *[[valid, case] for case in malformed],
        ]
        for document in documents:
            with self.subTest(document=document):
                fixture = self.root / "bad-evaluation.json"
                fixture.write_text(json.dumps(document))
                with (
                    contextlib.redirect_stdout(io.StringIO()) as output,
                    patch.object(RuleClassifier, "classify") as classify,
                ):
                    self.assertEqual(
                        main(
                            [
                                "evaluate",
                                "--input",
                                str(fixture),
                                "--output",
                                str(self.root / "metrics.json"),
                            ]
                        ),
                        1,
                    )
                classify.assert_not_called()
                self.assertIn("Error:", output.getvalue())
                self.assertFalse((self.root / "metrics.json").exists())

    def test_report_preserves_pending_delivery_state_on_classified_cards(self):
        from test_pipeline import Sink

        store = Store(self.root / "db")
        sink = Sink(fail=True)
        try:
            store.ingest([post()])
            process_pending(store, RuleClassifier(), sink)
            target = render_report(store, sink.destination, self.root / "pending.html")
            html = target.read_text()
            self.assertTrue(
                'data-label="BULLISH" data-state="pending"' in html,
                "Classified retry card must carry its pending delivery state",
            )
            self.assertIn("delivery_failed", html)
        finally:
            store.close()
