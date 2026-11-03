# Historical Jumpy implementations

These files preserve the recovered 2025 experiments. **They are not the maintained application.** The root README and `src/jumping_spyder/` describe the supported package.

- `node-prototype/`: Telegram interface, X polling, LLM prompt, Solana payment experiment.
- `python-worker/`: later X/YouTube processing, PostgreSQL schema, and notification worker.
- `n8n/`: workflow export with connection bindings and owner-specific metadata removed.

Known historical defects include placeholder subscription controls, message loss on failed delivery, latest-post-only handling, and unvalidated generated trading statistics. Old dependencies and external APIs have not been validated for current operation. Do not install or run these as part of the maintained app's quick start.

The runtime X checkpoint was removed; the n8n destination references `TELEGRAM_CHAT_ID` and would need new connection bindings if imported. No original live credentials, mnemonic, PostgreSQL dump, or runtime logs are distributed. See [history and migration](../docs/history.md).
