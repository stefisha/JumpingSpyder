# Verification and limits

The rebuild is verified as an offline application with mocked provider contracts. It has not been validated end to end against live X, YouTube, OpenAI, or Telegram accounts, and no live alerts or payments were sent during verification.

## Automated checks

Run `make check` with the project environment active:

- **39 unittest regressions** cover all unseen posts, source-qualified identities, duplicate ingestion, chronological processing across timezones, durable failed-delivery retries after restart, cached classification reuse, per-destination state, suppression rules, malformed model/fixture input, unsupported schema versions, and concurrent worker locking.
- Adapter tests inspect pagination, collection cutoffs, page-limit refusal, X partial errors, OpenAI JSON Schema requests, refusal/truncation handling, Telegram acknowledgment, plain-text formatting, HTTP retry bounds, and redacted failure messages.
- Report/CLI tests cover HTML escaping, literal environment loading, missing configuration, reproducible metrics, empty reports, demo idempotency, and a mocked preview-to-Telegram journey.
- Ruff checks maintained Python source, tests, and scripts. Archived prototype code is excluded from supported-runtime checks.

Run `make package` to build the source distribution and wheel. The package smoke script installs the wheel into a separate virtual environment and working directory, with no `PYTHONPATH` pointing at the checkout and no dependency downloads. It checks the CLI entry point, module entry point, bundled demo fixtures, HTML template, eight rendered cards, and 24-case evaluation. The wheel excludes archives, credentials, and runtime databases.

CI runs the suite and package smoke check on Ubuntu with Python 3.9 and 3.13, and compares the freshly generated baseline with the committed result. Local verification used Python 3.9 on macOS. Live provider access, quotas, model availability, and server behavior remain outside the mock tests.

## Manual browser checks

The generated report was inspected at desktop size and a 390 px phone viewport:

- The dark navy/green design uses the supplied original banner and exact supplied transparent logo; the logo is embedded in the offline HTML.
- Stance filtering shows four BULLISH cards out of eight unique sources.
- Text search narrows results to the matching source; a nonmatching search shows an explicit empty state.
- Complete-source disclosure opens independently of the evidence excerpt.
- The mobile document has a 390 px scroll width at a 390 px viewport, with one card per row.
- Filters and search are native keyboard-focusable controls. No decorative animation requires a motion setting.

Screenshots in `docs/assets/` capture the actual generated synthetic report. The HTML has no remote font, script, image, or stylesheet dependency. JavaScript enables filtering; all cards are readable without it.

## What these checks do not establish

The 24-case synthetic baseline evaluation does not measure real-world market-stance accuracy, safety detection effectiveness, return prediction, or profitability. Exact-excerpt validation proves the excerpt appears in the source; it does not prove semantic correctness. Network timeouts and crash windows can cause duplicate Telegram delivery. Provider-side content restrictions, edits, deletions, and outages longer than the configured collection window require operator handling. See architecture and evaluation for those boundaries.

## Protocol references

The adapters follow the documented REST formats; these links are reference contracts, not evidence that a live request succeeded:

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
- [X user posts](https://docs.x.com/x-api/users/get-posts)
- [YouTube playlistItems.list](https://developers.google.com/youtube/v3/docs/playlistItems/list)
- [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage)
