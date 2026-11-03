"""A small, synthetic challenge set: useful for regressions, never a market backtest."""

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from .domain import LABELS, Post, bounded


def evaluate(path, classifier, output):
    raw = Path(path).read_bytes()
    cases = json.loads(raw)
    if not isinstance(cases, list) or not cases or len(cases) > 10000:
        raise ValueError("Evaluation input must be a nonempty list of at most 10000 cases")
    seen = set()
    fields = {"id", "text", "label", "risk_flagged"}
    # Validate the entire dataset before any classifier can run or incur provider usage.
    for case in cases:
        if not isinstance(case, dict) or set(case) != fields:
            raise ValueError(
                "Each evaluation case must contain exactly id, text, label, risk_flagged"
            )
        bounded(case["id"], "evaluation ID", 200)
        bounded(case["text"], "evaluation text", 20000)
        if case["label"] not in LABELS or type(case["risk_flagged"]) is not bool:
            raise ValueError("Invalid evaluation annotation")
        if case["id"] in seen:
            raise ValueError("Evaluation case IDs must be unique")
        seen.add(case["id"])
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    results = []
    for case in cases:
        post = Post(
            "fixture",
            case["id"],
            "synthetic-evaluation",
            case["text"],
            "https://example.com/evaluation/" + quote(case["id"], safe=""),
            "2026-01-01T00:00:00Z",
        )
        result = classifier.classify(post)
        matrix[case["label"]][result.label] += 1
        results.append(
            {
                **case,
                "predicted": result.label,
                "predicted_risk": result.risk,
                "correct": result.label == case["label"],
            }
        )
    per_class = {}
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in LABELS if actual != label)
        fn = sum(matrix[label][predicted] for predicted in LABELS if predicted != label)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
            "support": sum(matrix[label].values()),
        }
    report = {
        "classifier": classifier.name,
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_kind": "author-labeled synthetic challenge set; not independent validation",
        "samples": len(cases),
        "accuracy": sum(r["correct"] for r in results) / len(results),
        "macro_f1": sum(r["f1"] for r in per_class.values()) / len(LABELS),
        "risk_flag_accuracy": sum(
            (r["predicted_risk"] == "FLAGGED") == r["risk_flagged"] for r in results
        )
        / len(results),
        "confusion_matrix": matrix,
        "per_class": per_class,
        "cases": results,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
