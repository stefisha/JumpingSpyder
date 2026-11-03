"""Explicit CLI modes keep credential-free review separate from live notifications."""

import argparse
import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path

from .classifiers import OpenAIClassifier, RuleClassifier
from .evaluation import evaluate
from .http import JsonHTTP, ProviderError
from .pipeline import process_pending
from .report import render_report
from .sinks import PreviewSink, TelegramSink
from .sources import FixtureSource, XSource, YouTubeSource
from .store import Store


def load_env(path):
    """Read literal KEY=VALUE assignments; never execute shell content or overwrite env."""
    import re

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Environment file requires literal KEY=VALUE assignments")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value


def classifier_for(args, http):
    if args.classifier == "rules":
        return RuleClassifier()
    return OpenAIClassifier(http, required("OPENAI_API_KEY"), required("OPENAI_MODEL"))


def sink_for(args, http):
    if args.notify:
        return TelegramSink(http, required("TELEGRAM_BOT_TOKEN"), required("TELEGRAM_CHAT_ID"))
    return PreviewSink()


def positive(value):
    number = int(value)
    if number < 1 or number > 10000:
        raise argparse.ArgumentTypeError("Must be between 1 and 10000")
    return number


def parser():
    root = argparse.ArgumentParser(
        description="Collect, classify, and review source-linked social content."
    )
    root.add_argument(
        "--env-file", type=Path, help="Optional literal KEY=VALUE file; shell environment wins"
    )
    root.add_argument("--version", action="version", version="JumpingSpyder 0.2.0")
    sub = root.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the synthetic offline demo; no accounts or network")
    demo.add_argument("--output", type=Path, default=Path("reports/demo"))
    demo.add_argument(
        "--database", type=Path, help="Persistent demo database; default is OUTPUT/demo.sqlite3"
    )
    evaluation = sub.add_parser(
        "evaluate", help="Measure the offline baseline on synthetic challenge cases"
    )
    evaluation.add_argument("--input", type=Path)
    evaluation.add_argument("--output", type=Path, default=Path("reports/evaluation.json"))
    for name, help_text in (
        ("ingest", "Import source records from JSON"),
        ("sync", "Fetch a bounded recent window from X or YouTube"),
        ("retry", "Retry the durable backlog without fetching sources"),
        ("report", "Render a snapshot without processing content"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--database", type=Path, default=Path("data/jumpy.sqlite3"))
        cmd.add_argument("--report", type=Path, default=Path("reports/review.html"))
        cmd.add_argument(
            "--notify",
            action="store_true",
            help="Select real Telegram delivery (requires credentials)",
        )
        if name != "report":
            cmd.add_argument("--classifier", choices=("rules", "openai"), default="rules")
            cmd.add_argument("--limit", type=positive, default=100)
        if name == "ingest":
            cmd.add_argument("--input", required=True, type=Path)
        if name == "sync":
            cmd.add_argument("--source", choices=("x", "youtube"), required=True)
            cmd.add_argument(
                "--accounts",
                required=True,
                help="Comma-separated X usernames or canonical YouTube UC IDs",
            )
            cmd.add_argument("--pages", type=positive, default=3)
            cmd.add_argument("--since", help="UTC ISO timestamp; defaults to seven days ago")
    return root


def execute(args):
    if args.env_file:
        load_env(args.env_file)
    if args.command == "evaluate":
        path = args.input or files("jumping_spyder").joinpath("data/evaluation.json")
        result = evaluate(path, RuleClassifier(), args.output)
        print(
            json.dumps(
                {k: result[k] for k in ("samples", "accuracy", "macro_f1", "risk_flag_accuracy")}
            )
        )
        print(f"Synthetic evaluation: {args.output}")
        return 0
    if args.command == "demo":
        output = args.output
        with_store = Store(args.database or output / "demo.sqlite3")
        try:
            with with_store.lock():
                source = files("jumping_spyder").joinpath("data/demo.json")
                posts = FixtureSource(source).fetch()
                added = with_store.ingest(posts)
                stats = process_pending(with_store, RuleClassifier(), PreviewSink())
                path = render_report(
                    with_store, "local-review", output / "index.html", "Offline / synthetic demo"
                )
            print(json.dumps({"fetched": len(posts), "inserted": added, **asdict(stats)}))
            print(f"Open {path.resolve()}")
            return int(stats.failed > 0)
        finally:
            with_store.close()
    http = JsonHTTP()
    sink = sink_for(args, http)
    classifier = classifier_for(args, http) if args.command != "report" else None
    store = Store(args.database)
    failed_sources = 0
    try:
        with store.lock():
            if args.command == "ingest":
                print(f"Inserted {store.ingest(FixtureSource(args.input).fetch())} source records")
            if args.command == "sync":
                since = args.since or (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                stamp = datetime.fromisoformat(since.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    raise ValueError("--since must include a timezone")
                if stamp >= datetime.now(timezone.utc):
                    raise ValueError("--since must be in the past")
                since = stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
                if not accounts:
                    raise ValueError("At least one account is required")
                if args.source == "x":
                    token = required("X_BEARER_TOKEN")
                    sources = [XSource(http, token, a, args.pages, since) for a in accounts]
                else:
                    token = required("YOUTUBE_API_KEY")
                    sources = [YouTubeSource(http, token, a, args.pages, since) for a in accounts]
                for source in sources:
                    try:
                        store.ingest(source.fetch())
                    except Exception as error:
                        failed_sources += 1
                        # Report source position, never credential-bearing provider exceptions.
                        detail = (
                            str(error)
                            if isinstance(error, ProviderError) or type(error) is ValueError
                            else "check source configuration and response shape"
                        )
                        print(
                            f"Source {sources.index(source) + 1} failed: {detail}; inbox unchanged for that source"
                        )
            stats = process_pending(store, classifier, sink, args.limit) if classifier else None
            render_report(
                store,
                sink.destination,
                args.report,
                "Telegram delivery" if args.notify else "Local review / no external delivery",
            )
            if stats:
                print(json.dumps({"source_failures": failed_sources, **asdict(stats)}))
            print(f"Review snapshot: {args.report.resolve()}")
            return int(failed_sources > 0 or (stats is not None and stats.failed > 0))
    finally:
        store.close()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return execute(args)
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        # Only our own validation strings are safe to display; file/OS errors may contain paths.
        if type(error) is ValueError or isinstance(error, ProviderError):
            print(f"Error: {error}")
        else:
            print("Error: operation failed; check paths, database access, and worker locking")
        return 1
