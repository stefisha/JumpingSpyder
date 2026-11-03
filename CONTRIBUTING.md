# Contributing

The supported application is `src/jumping_spyder/`. Keep archived prototypes outside the maintained import path. Do not commit credentials, collected social content, SQLite files, local reports, logs, or provider payloads.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-build-isolation
make check
make package
```

Tests use the standard library's unittest framework and fake HTTP clients. They must not require API credentials, send Telegram messages, contact live APIs, or use production data. New integration behavior should be covered at its request/response boundary and by a relevant pipeline regression.

Before submitting a change:

- Run the checks above. Update docs when commands, contracts, or scope change.
- If changing the rules baseline, update its version, regenerate `docs/results/baseline.json`, and explain newly changed errors in `docs/evaluation.md`.
- If changing persistence, add a schema version/migration strategy and restart/retry coverage.
- If changing the report, generate the demo, inspect desktop and mobile layouts, and exercise keyboard navigation, filters, search, full-text disclosure, and the empty state. Regenerate the README screenshot when it changes.

Ruff is configured in `pyproject.toml`. `make format` applies formatting and import fixes. No frontend build is required; the report template contains its own styles and a small static filtering script. The green pixel-spider identity comes from the supplied original banner.
