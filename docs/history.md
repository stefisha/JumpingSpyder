# Project history and migration

JumpingSpyder began as **Jumpy**, an experimental 2025 crypto-signal project combining social monitoring, an LLM classifier, Telegram alerts, and a Solana premium-access prototype. The recovered VM source was cross-referenced against the original repository in September 2026. The Node checkout held a later bot interface; the Python worker had not previously been committed.

The 2026 portfolio rebuild keeps that history while making the maintained application reproducible and inspectable:

| Previous location | New location              | Status                                                           |
| ----------------- | ------------------------- | ---------------------------------------------------------------- |
| `jumping_spyder/` | `archive/node-prototype/` | Historical Telegraf bot, scanner, classifier, payment experiment |
| `jumpys_bot/`     | `archive/python-worker/`  | Historical X/YouTube worker and empty PostgreSQL schema          |
| `workflow/`       | `archive/n8n/`            | Sanitized n8n workflow export                                    |
| —                 | `src/jumping_spyder/`     | Maintained application and CLI                                   |

The old runtime checkpoint `xscanner/store.json` was removed. The n8n export now omits original credential bindings, webhook IDs, and instance metadata; fixed destination IDs are replaced with an environment reference. Source code remains available for historical inspection. It is not included in the built wheel, tested as a supported runtime, or used by the maintained application's commands.

## Changes in product scope

The original prompts mixed sentiment, scam detection, account-compromise judgments, return forecasts, and generated “historical accuracy.” The maintained application separates expressed stance from a limited text-based risk flag and requires a source excerpt. It does not create trading targets or claim calibrated confidence.

SQLite removes the original PostgreSQL dependency for a small local worker. The app fetches all posts returned within a bounded window rather than analyzing only the newest. Classification is saved before delivery; failed delivery stays pending. Telegram subscription, token watchlists, and Solana payments were never a complete service and are not presented as supported features.

YouTube now uses canonical channel IDs and upload-playlist metadata. Transcript extraction and implicit display-name channel search were removed from the maintained path. This reduces dependencies and ambiguity, with the explicit limitation that classification sees only title and description.

## Existing deployments

Do not point the new application at the old PostgreSQL database or copy old configuration wholesale. Install the new package, use a new SQLite path, choose current credentials, configure the required variables, and inspect the offline demo first. Historical credentials should remain revoked. Old cron jobs and `run_bot.sh` are archival references, not maintained installation instructions.
