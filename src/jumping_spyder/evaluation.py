"""A small, synthetic challenge set: useful for regressions, never a market backtest."""

import hashlib
import json
from pathlib import Path

from .domain import LABELS, Post


def evaluate(path, classifier, output):
    raw = Path(path).read_bytes()
    cases = json.loads(raw)
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Evaluation cases must be nonempty with unique IDs")
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    results = []
    for case in cases:
        if case["label"] not in LABELS or type(case["risk_flagged"]) is not bool:
            raise ValueError("Invalid evaluation annotation")
        post = Post(
            "fixture",
            case["id"],
            "synthetic-evaluation",
            case["text"],
            "https://example.com/evaluation/" + case["id"],
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
