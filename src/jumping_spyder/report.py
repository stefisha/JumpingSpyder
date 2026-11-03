"""Self-contained review artifact; all source/model strings are escaped as text."""

import base64
from collections import Counter
from datetime import datetime, timezone
from html import escape
from importlib.resources import files
from pathlib import Path


def render_report(store, destination, output, mode="Local review"):
    records = store.records(destination)
    labels, states = Counter(), Counter()
    cards = []
    for row in records:
        post, result = store.decode(row)
        label = result.label if result else "PENDING"
        labels[label] += 1
        state = row["state"] or "pending"
        states[state] += 1
        display_state = (
            "reviewed locally" if state == "delivered" and destination == "local-review" else state
        )
        risk = result.risk if result else "UNKNOWN"
        summary = (
            result.summary
            if result
            else "Classification is pending. Retry the worker to process this item."
        )
        excerpt = result.evidence if result else post.text[:240]
        error = row["delivery_error"] or row["error"]
        failure = (
            '<span class="error">Retry pending · ' + escape(error) + "</span>" if error else ""
        )
        cards.append(f'''<article class="card" data-label="{label}">
          <div class="card-top"><span class="source">{escape(post.source)} / {escape(post.author)}</span>
          <span class="tag {label.lower()}">{label}</span></div>
          <h3>{escape(summary)}</h3><blockquote>{escape(excerpt)}</blockquote>
          <details><summary>Read complete source text</summary><p class="full-text">{escape(post.text)}</p></details>
          <div class="card-bottom"><a href="{escape(post.url, quote=True)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>
          <time datetime="{escape(post.published_at, quote=True)}">{escape(post.published_at[:10])}</time></div>
          <div class="card-state"><span>Risk check: {risk}</span><span>{display_state}</span>{failure}</div>
          <div class="provenance">{escape(post.key)} · {escape(row["classifier"] or "awaiting classifier")} · delivery attempts {row["delivery_attempts"] or 0}</div>
        </article>''')
    template = files("jumping_spyder").joinpath("templates/review.html").read_text(encoding="utf-8")
    logo = files("jumping_spyder").joinpath("templates/logo.png").read_bytes()
    values = {
        "LOGO": "data:image/png;base64," + base64.b64encode(logo).decode("ascii"),
        "MODE": escape(mode),
        "GENERATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "TOTAL": str(len(records)),
        "DIRECTIONAL": str(labels["BULLISH"] + labels["BEARISH"]),
        "SUPPRESSED": str(states["suppressed"]),
        "PENDING": str(states["pending"]),
        "CARDS": "\n".join(cards)
        or '<p class="empty">No content yet. Run the demo or ingest a fixture.</p>',
    }
    # One pass prevents user content containing template markers from being substituted again.
    import re

    document = re.sub(r"@@([A-Z]+)@@", lambda match: values[match[1]], template)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output
