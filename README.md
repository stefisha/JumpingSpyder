# Jumping Spyder

Archived source for **Jumpy**, an experimental 2025 crypto-signal startup. It watched selected X/Twitter accounts and YouTube channels, used an LLM to classify possible trading signals, sent alerts through Telegram, and experimented with Solana-based premium access.

This repository preserves both implementations recovered from the original VM:

- [`jumping_spyder/`](jumping_spyder/) — the original Node.js/Telegraf bot, X scanner, LLM signal validator, and Solana payment-gate prototype.
- [`jumpys_bot/`](jumpys_bot/) — the later Python worker for X and YouTube monitoring, PostgreSQL memory, LLM classification, and Telegram notifications.
- [`workflow/`](workflow/) — the original workflow export.

The VM versions were cross-referenced against the original repository in September 2026. The Node.js checkout contained a later `bot.js`; the Python implementation had never been committed and was recovered in full.

## Security and archival notes

This is a public source archive. The following runtime material was deliberately **not** committed:

- real `.env` files and API tokens;
- the Solana mnemonic;
- Telegram, OpenAI, X/Twitter, and YouTube credentials;
- the PostgreSQL data dump, which contained processed social-media content;
- runtime logs, dependency folders, caches, and Python bytecode.

Only placeholder environment templates and the empty database schema are included. Any credentials once used by this retired project should remain revoked.

## Node.js prototype

```bash
cd jumping_spyder
npm install
cp .env.example .env
# Fill in your own credentials, then:
node bot.js
```

Important files:

- `bot.js` — Telegram interface and waitlist flow.
- `cron.js` / `demo.js` — X scanning and signal processing.
- `ai/validateSignal.js` — OpenAI-based signal classifier.
- `solana/paymentGate.js` — deterministic Solana address prototype.

## Python signal worker

```bash
cd jumpys_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
createdb tweets
psql tweets < schema.sql
python main.py
```

`main.py` processes X posts; `youtube.py` handles recent YouTube uploads. The original cron entries existed on the VM but were disabled when archived.

## Status

Historical and unmaintained. The code uses older APIs/models and is preserved for reference rather than production deployment.

## License

MIT License © 2025 Jumping Spyder
