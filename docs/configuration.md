# Configuration

No configuration is needed for `demo` or `evaluate`. Other commands accept an optional global `--env-file` before the subcommand:

```sh
jumping-spyder --env-file .env ingest --input examples/posts.json --classifier openai
```

The parser supports literal `KEY=VALUE` lines, optional matching quotes, blank lines, and full-line comments. It does not execute shell syntax, interpolate variables, accept `export`, or strip inline comments. Existing shell variables take precedence, including empty values. Restart a scheduled process after configuration changes.

| Variable             | Required for            | Meaning                                                                |
| -------------------- | ----------------------- | ---------------------------------------------------------------------- |
| `X_BEARER_TOKEN`     | `sync --source x`       | X API bearer token with timeline access                                |
| `YOUTUBE_API_KEY`    | `sync --source youtube` | YouTube Data API key                                                   |
| `OPENAI_API_KEY`     | `--classifier openai`   | OpenAI API credential                                                  |
| `OPENAI_MODEL`       | `--classifier openai`   | A model available to your account supporting strict JSON Schema output |
| `TELEGRAM_BOT_TOKEN` | `--notify`              | Telegram bot credential                                                |
| `TELEGRAM_CHAT_ID`   | `--notify`              | Destination the bot can message                                        |

The maintained app does not use the old archive's `DATABASE_URL`, mnemonic, `TRACKED_USERS`, or cron environment settings. CLI arguments select accounts, data paths, and collection windows explicitly. See `jumping-spyder --help` and each subcommand's `--help`.

## JSON source contract

`ingest --input` accepts a UTF-8 JSON array of up to 10,000 records. Example:

```json
[
  {
    "source": "fixture",
    "id": "sample-001",
    "author": "synthetic-author",
    "text": "I am bullish on the project after reading the release notes.",
    "url": "https://example.com/posts/sample-001",
    "published_at": "2026-01-15T09:00:00Z"
  }
]
```

Allowed sources are `fixture`, `x`, and `youtube`. IDs and authors are nonempty strings up to 200 characters; source text is nonempty and at most 20,000 characters. URLs must be absolute HTTPS URLs without embedded credentials and at most 2,000 characters. Timestamps must include a timezone. X usernames are normalized to lowercase before constructing source records. IDs must remain stable across polling runs; a source ID with changed content is rejected for reconciliation.

The text sent to the classifier is the complete stored text. `evidence` is limited to 600 characters and must be an exact substring; `summary` is limited to 600 characters. Invalid output stays pending rather than becoming an alert. API credentials never belong in source JSON.

## Files and privacy

Runtime data is excluded from Git. SQLite contains original collected text; reports contain excerpts, full text, and source links. Treat both as content exports and share only what you intend to disclose. The database file is created with owner-only permissions; directory permissions, report permissions, backups, and retention remain the operator's responsibility. Only synthetic demo/evaluation assets are committed.

Provider errors are reduced to generic failure codes in storage. The HTTP transport emits status codes or generic transport errors rather than credential-bearing URLs or provider payloads. Archived credentials are placeholders; the retired project's credentials should remain revoked.
