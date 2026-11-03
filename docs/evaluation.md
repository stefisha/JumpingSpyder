# Evaluation

The committed result measures the deterministic `rules-v1` baseline on **24 author-labeled synthetic English examples**. It is a challenge set for inspecting behavior, not an independent benchmark, financial backtest, or production model validation. Cases were written alongside the rules and include obvious successes and deliberate failure modes; they are not a held-out random sample.

## Reproduce

```sh
jumping-spyder evaluate --output reports/evaluation.json
```

The packaged cases are in [`src/jumping_spyder/data/evaluation.json`](../src/jumping_spyder/data/evaluation.json). [`results/baseline.json`](results/baseline.json) records each expected/predicted label, risk outcome, confusion matrix, per-class metrics, classifier version, and SHA-256 of the exact dataset bytes. No live model calls or network access are involved.

| Metric              |                         Result |
| ------------------- | -----------------------------: |
| Examples            |                             24 |
| Stance accuracy     |                  62.5% (15/24) |
| Macro F1            |                          0.665 |
| Risk flag agreement | 24/24 on these synthetic cases |

Risk agreement is not a measured real-world scam-detection rate. The set has only three flagged examples and directly exposes the baseline's configured trigger phrases.

## Confusion matrix

Rows are author-assigned expected labels; columns are predictions. Counts, not percentages:

| Expected / predicted | BULLISH | BEARISH | NEUTRAL | UNCERTAIN |
| -------------------- | ------: | ------: | ------: | --------: |
| BULLISH              |       4 |       0 |       3 |         0 |
| BEARISH              |       0 |       4 |       3 |         0 |
| NEUTRAL              |       1 |       1 |       4 |         0 |
| UNCERTAIN            |       0 |       0 |       1 |         3 |

Macro F1 gives each label equal weight. Undefined precision/recall contributions are zero. Every row-level result, including the nine errors, is preserved in the JSON output.

## What the errors show

- **Paraphrases:** “I expect this project to outperform” expresses optimism without a configured keyword; the baseline predicts NEUTRAL.
- **Definitions and quotations:** “What does bullish mean in trading?” contains a trigger word but expresses no author's market stance; the baseline predicts BULLISH.
- **Ambiguity:** “Maybe it rises, maybe it falls” should be UNCERTAIN but has no directional keyword, so it becomes NEUTRAL.
- **Identity and context:** keyword risk checks cannot verify authorship, diagnose a hacked account, or establish that a link is safe.

The baseline is useful for a deterministic, account-free demonstration of collection, validation, persistence, filtering, and delivery. Its errors make clear why wording alone is insufficient for dependable interpretation.

## Next evaluation milestone

Build a permission-appropriate, independently labeled real-content dataset with written annotation rules, two annotators and disagreement review, a held-out split, varied accounts, time-separated examples, paraphrases, sarcasm, quoted speech, mixed language, and adversarial content. Evaluate the configured model on the same dataset; report stance metrics, refusal/invalid-output rate, risk precision/recall, latency, and cost. Use separate databases per classifier to avoid reusing cached results. Do not infer return prediction accuracy from stance classification.
