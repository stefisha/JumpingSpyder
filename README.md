<p align="center"><img src="docs/assets/banner.png" alt="JumpingSpyder — green pixel spider against a dark market-chart backdrop" width="100%"></p>

<h1 align="center">JumpingSpyder</h1>
<p align="center"><strong>Catch the stance. Keep the context.</strong><br>Source-linked social content classification, durable processing, and an inspectable review desk.</p>
<p align="center">
  <a href="https://github.com/stefisha/JumpingSpyder/actions/workflows/checks.yml"><img src="https://github.com/stefisha/JumpingSpyder/actions/workflows/checks.yml/badge.svg" alt="Checks"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-5cdb82?logo=python&logoColor=white" alt="Python 3.9 or newer">
  <img src="https://img.shields.io/badge/runtime_dependencies-0-5cdb82" alt="Zero third-party runtime dependencies">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
</p>
<p align="center"><a href="#try-it-in-two-minutes">Try the demo</a> · <a href="docs/architecture.md">Architecture</a> · <a href="docs/evaluation.md">Measured baseline</a> · <a href="docs/running.md">Run & configure</a> · <a href="docs/history.md">Project history</a></p>

JumpingSpyder collects posts from X and upload metadata from YouTube, classifies the author's expressed market stance, and attaches a source excerpt to every result. A local HTML review report exposes the classification, risk flag, provenance, and delivery state. Optional Telegram delivery uses a persistent retry queue.

Originally built as **Jumpy**, a 2025 crypto-signal experiment, the project now has one maintained Python application. The recovered Node.js bot, Python worker, and n8n workflow remain in [`archive/`](archive/) as historical context.

**Status:** tested offline application and mocked live-adapter contracts. Live provider behavior has not been verified with real credentials. Classifications describe source content; they do not establish trading profitability, scam-detection accuracy, or account authenticity. There is no trading execution or payment collection in the maintained application.

## Try it in two minutes

Requires **Python 3.9+ on macOS or Linux**. No API keys, database server, or frontend build are needed.

```sh
git clone https://github.com/stefisha/JumpingSpyder.git
cd JumpingSpyder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
jumping-spyder demo
```

Open **`reports/demo/index.html`** in your browser. It is a self-contained snapshot with search, stance filters, full-source inspection, and delivery state; there is no running web server or external asset request.

The demo supplies **nine records representing eight unique synthetic posts**. Four directional, unflagged items are reviewed locally; four neutral, conflicting, or flagged items are suppressed from alerts. Run it again to see deduplication: **zero new records and zero repeat deliveries**. “Delivered” in demo CLI output refers to the local review destination; no messages leave your machine.

<p align="center"><img src="docs/assets/review-desktop.png" alt="Dark JumpingSpyder review desk showing source counts, searchable classifications, evidence excerpts, and review status" width="100%"></p>

## The landing page

The original product used a public landing page to introduce Jumpy and direct visitors to Telegram. The rebuilt [landing page](web/landing/README.md) preserves its dark/green identity and original artwork, with responsive navigation, a Telegram example, and keyboard-accessible FAQs.

The original alpha delivered to one shared chat. Individual bot messages and subscriber preferences are planned features, not functionality supplied by the landing page. The Python worker and static website can be hosted separately.

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory web/landing
```

<p align="center"><img src="docs/assets/landing-desktop.png" alt="Rebuilt JumpingSpyder landing page using the original green spider branding and Telegram hero artwork" width="100%"></p>

## What the engineering demonstrates

| Concern                             | Implementation                                                                                                          |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Missed posts between polling runs   | Collect every returned item across pages within an explicit time window; refuse silently truncated page-limited batches |
| Duplicate classification and alerts | Source-qualified primary keys, cached validated classifications, and per-destination delivery records                   |
| Failed Telegram delivery            | Keep the item pending; retry from SQLite after restart without calling the classifier again                             |
| Model output reliability            | Strict JSON Schema request, local enum/type validation, exact-excerpt validation, refusal/truncation handling           |
| Inspectability                      | Source URLs, complete source text, classifier identity, processing errors, and delivery attempt counts                  |
| Reproducibility                     | Credential-free fixtures, labeled challenge cases, regression tests, CI, and an installed-wheel smoke test              |

Delivery is **at least once**, not exactly once: if Telegram accepts a message but the worker crashes before recording the acknowledgment, a retry can duplicate that message. Every alert includes a stable source reference. See [failure handling](docs/architecture.md#failure-handling).

## Classifiers and measured results

- **`rules`** is the default offline keyword baseline. It is deterministic and inspectable, but fails on paraphrases, quoted language, and some ambiguity.
- **`openai`** is an optional model adapter with a configurable model and validated structured output. It has not been evaluated live in this rebuild.

On the included **24 author-labeled synthetic challenge cases**, `rules-v1` scored **62.5% stance accuracy** and **0.665 macro F1**. The mistakes are retained in the [full results](docs/results/baseline.json). These cases demonstrate implementation behavior, not generalization to real social content or market outcomes.

```sh
jumping-spyder evaluate
```

See [evaluation methodology, confusion matrix, and known errors](docs/evaluation.md). There are no invented confidence percentages, return targets, or “historical accuracy” fields.

## Import your own source records

```sh
jumping-spyder ingest --input examples/posts.json
jumping-spyder retry
jumping-spyder report
```

The default inbox is `data/jumpy.sqlite3`; the default report is `reports/review.html`. These commands use the local review destination. Adding `--notify` selects Telegram and requires its credentials. Changing classifier flags does not overwrite cached classifications; use a new database to compare classifiers.

For live X/YouTube collection, OpenAI configuration, retry behavior, and scheduling, use the [running guide](docs/running.md). The [configuration reference](docs/configuration.md) documents the JSON input contract and all environment variables.

## Project structure

```text
src/jumping_spyder/    Maintained package and CLI
  domain.py           Validated source and classification contracts
  sources.py          Fixture, X timeline, and YouTube metadata collectors
  classifiers.py      Rules baseline and optional OpenAI adapter
  store.py            SQLite inbox, classifications, and delivery records
  pipeline.py         Failure isolation and retry processing
  sinks.py            Local review and Telegram destinations
  report.py           Escaped, self-contained HTML generation
  data/               Packaged synthetic demo and evaluation cases
  templates/          Self-contained review interface
examples/             Input examples
web/landing/          Static public-facing landing page and local assets
tests/               Regression and adapter-contract tests
docs/                Architecture, configuration, evaluation, screenshots
archive/             Historical implementations; not installed or maintained
.github/workflows/    Automated checks and package verification
```

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-build-isolation
make check
```

`make check` runs Ruff and the offline regression suite. `make package` builds a wheel and verifies the installed CLI, packaged demo data, and report template from outside the checkout. See [CONTRIBUTING.md](CONTRIBUTING.md) and [verification scope](docs/verification.md).

## License

[MIT](LICENSE). Original Jumpy / Jumping Spyder project, 2025; maintained portfolio application, 2026. The supplied project banner retains the original green pixel-spider identity.
