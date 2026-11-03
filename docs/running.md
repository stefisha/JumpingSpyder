# Running JumpingSpyder

## Offline first

Install from the repository root as shown in the README. The CLI and `python -m jumping_spyder` are equivalent. Both work from outside the checkout after installation; fixtures and the HTML template are package data.

```sh
jumping-spyder demo
jumping-spyder evaluate
jumping-spyder ingest --input examples/posts.json
```

The demo uses `reports/demo/demo.sqlite3`, separate from the normal `data/jumpy.sqlite3`. Use a different `--output` directory to start a fresh demo. Re-running against the same demo database demonstrates deduplication.

## Configure optional live adapters

Create `.env` only if it does not already exist:

```sh
python -c "from pathlib import Path; p=Path('.env'); p.exists() or p.write_bytes(Path('.env.example').read_bytes())"
```

Fill only the credentials you need. Keep the file local. Choose an OpenAI model that supports strict JSON Schema output; no model is silently selected for you.

The following commands make live provider requests and may consume provider quota. They are examples; the rebuild's verification uses mocks and synthetic data.

```sh
# X usernames, without @. Default collection window: last seven days.
jumping-spyder --env-file .env sync --source x --accounts example_account --classifier openai

# Canonical UC channel IDs, not display names. YouTube analyzes titles/descriptions.
jumping-spyder --env-file .env sync --source youtube --accounts UCabcdefghijklmnopqrstuv --classifier openai

# Enable real Telegram notifications for queued directional, unflagged content.
jumping-spyder --env-file .env retry --notify
```

`sync` with no `--notify` uses local review. Previously reviewed posts can still be delivered when `--notify` is later selected. Use `sync --notify` to collect and deliver in the same run. Review credentials and destination before opting into live delivery; the demo never uses them.

A `retry` reuses a saved classification, even if a different `--classifier` is selected. That flag controls only posts not yet successfully classified. A new empty database is the simplest way to compare classifier configurations.

## Backlog, failures, and reporting

```sh
# Catch up after a longer outage; use the actual UTC start time you need.
jumping-spyder --env-file .env sync --source x --accounts example_account --since 2026-01-01T00:00:00Z --pages 20

# Process up to 500 pending entries without refetching source feeds.
jumping-spyder --env-file .env retry --notify --limit 500

# Refresh the Telegram destination's snapshot without classifying or sending anything.
jumping-spyder --env-file .env report --notify
```

`--pages` defaults to 3; X pages request 100 posts, YouTube pages request 50 uploads. Reaching the page limit with more in-window content fails that source rather than silently dropping items. Increase `--pages` or choose a narrower window, then rerun. Each processing run handles at most `--limit` pending entries (default 100); run `retry` again while the report shows pending items.

Exit code 0 means the requested batch ran without source/classification/delivery failures; it does not mean no backlog remains. Exit code 1 signals a failure; argparse uses exit code 2 for invalid CLI syntax. Failed classifications and sends remain pending. A different source failing during `sync` does not prevent processing the existing inbox.

Local review states appear as “reviewed locally” in the HTML. Telegram shows delivered, pending, or suppressed. The report is a static snapshot: regenerate it after processing. It opens directly from disk; filters/search are client-side and require JavaScript. All cards remain visible when JavaScript is unavailable.

## Scheduling

Use an external scheduler (cron, launchd, or a service timer) to call `sync`, then `retry` as needed. Use absolute paths to the executable, environment file, database, and report. An advisory lock refuses concurrent runs against the same SQLite file; store it on a local disk. Example cron entry, adjusted for your paths:

```cron
*/15 * * * * /absolute/project/.venv/bin/jumping-spyder --env-file /absolute/project/.env sync --source x --accounts example_account --classifier openai --notify --database /absolute/project/data/jumpy.sqlite3 --report /absolute/project/reports/review.html
```

Scheduling is external: `CRON_SCHEDULE` and `SCAN_INTERVAL_MINUTES` from old prototypes do not configure the maintained worker.

## Troubleshooting

| Symptom                                         | Action                                                                                                                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| CLI not found                                   | Activate the virtual environment; try `python -m jumping_spyder --help`                                                   |
| Missing environment variable                    | Set the named variable; place `--env-file` before the subcommand                                                          |
| Source failed                                   | Check account IDs, provider permissions and quotas, `--since`, and the page cap; existing inbox content remains available |
| Pending classification                          | Check model support for JSON Schema, provider connectivity, refusal, and output validation                                |
| Pending Telegram send                           | Check bot/chat access and retry with `--notify`; do not assume a timeout means the message was not accepted               |
| Preview has data but Telegram report is pending | Destinations have independent state; run `retry --notify`                                                                 |
| Changed content rejected                        | Preserve the existing evidence snapshot; reconcile edited source IDs explicitly or use a separate database                |
| Concurrent worker refused                       | Wait for the active process; OS locks release automatically when it exits                                                 |
| Old model appears on a card                     | Saved classifications are reused; use a fresh database for another experiment                                             |
